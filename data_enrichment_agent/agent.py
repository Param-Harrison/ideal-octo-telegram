from typing import Any
from google.adk.agents.llm_agent import Agent
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup

# Shared model configuration
model = LiteLlm(model='openrouter/google/gemini-2.0-flash-001')

# State keys
STATE_WEBSITE_URL = "website_url"
STATE_SOCIAL_LINKS = "social_links"
STATE_CEO_INFO = "ceo_info"
STATE_CEO_CANDIDATES = "ceo_candidates"
STATE_CEO_VALIDATION_RESULT = "ceo_validation_result"
STATE_COMPANY_SUMMARY = "company_summary"

# Tool: Search for company website
def search_company_website(company_name: str) -> str:
    """Search for the official company website URLs.
    
    Args:
        company_name: The name of the company
    
    Returns:
        str: The top search result URL that appears to be the company's official website
    """
    try:
        with DDGS() as ddgs:
            query = f"{company_name} official website"
            results = list(ddgs.text(query, max_results=5))

            # Return as comma separated string
            if results:
                return ", ".join([r.get("href", "") for r in results])
            return ""
    except Exception as e:
        print(f"Error searching for website: {e}")
        return ""

# Tool: Search for a specific social media platform (returns top 3 links)
def search_social_platform(company_name: str, platform: str, website: str = None) -> list:
    """Search for social media profile links for a specific platform and return top 3 results.
    
    Args:
        company_name: The name of the company
        platform: The social media platform (linkedin, twitter)
        website: Optional company website URL
    
    Returns:
        list: List of top 3 potential URLs for the platform
    """
    results = []
    
    try:
        with DDGS() as ddgs:
            platform_lower = platform.lower()
            
            if platform_lower == "linkedin":
                query = f"{company_name} LinkedIn company page"
                for r in ddgs.text(query, max_results=3):
                    url = r.get("href", "")
                    if "linkedin.com" in url.lower():
                        results.append(url)
            
            elif platform_lower in ["twitter", "x"]:
                query = f"{company_name} Twitter X official account"
                for r in ddgs.text(query, max_results=3):
                    url = r.get("href", "")
                    if any(domain in url.lower() for domain in ["twitter.com", "x.com"]):
                        results.append(url)
    except Exception as e:
        print(f"Error searching for {platform}: {e}")
    
    return results

# Tool: Search for top 3 CEO candidates
def search_ceo_candidates(company_name: str, website: str = None) -> list:
    """Search for top 3 CEO candidates for a company.
    
    Args:
        company_name: The name of the company
        website: Optional company website URL
    
    Returns:
        list: List of CEO candidate names (top 3)
    """
    candidates = []
    try:
        with DDGS() as ddgs:
            query = f"{company_name} CEO name"
            results = list(ddgs.text(query, max_results=5))
            
            # Extract potential CEO names from results
            for r in results:
                title = r.get('title', '')
                snippet = r.get('body', '')
                text = f"{title} {snippet}".lower()
                
                # Look for patterns like "CEO [Name]" or "[Name] CEO" or "[Name], CEO"
                # This is a simple extraction - the LLM will refine it
                candidates.append({
                    'title': r.get('title', ''),
                    'snippet': r.get('body', ''),
                    'url': r.get('href', '')
                })
                
                if len(candidates) >= 3:
                    break
    except Exception as e:
        print(f"Error searching for CEO candidates: {e}")
    
    return candidates

# Tool: Validate CEO candidate by searching for mentions with company
def validate_ceo_candidate(ceo_name: str, company_name: str) -> dict:
    """Validate a CEO candidate by searching for mentions of the person with the company on social media/blogs.
    
    Args:
        ceo_name: The CEO candidate name to validate
        company_name: The name of the company
    
    Returns:
        dict: Validation results with mention count and sources
    """
    try:
        with DDGS() as ddgs:
            # Search for mentions of CEO + company on various platforms
            queries = [
                f'"{ceo_name}" "{company_name}" CEO',
                f'"{ceo_name}" "{company_name}" LinkedIn',
                f'"{ceo_name}" "{company_name}" Twitter',
                f'"{ceo_name}" "{company_name}" blog',
            ]
            
            total_mentions = 0
            sources = []
            
            for query in queries:
                results = list(ddgs.text(query, max_results=3))
                total_mentions += len(results)
                
                for r in results:
                    url = r.get('href', '')
                    # Check if it's from a credible source
                    if any(domain in url.lower() for domain in [
                        'linkedin.com', 'twitter.com', 'x.com', 
                        'crunchbase.com', 'bloomberg.com', 'forbes.com',
                        'techcrunch.com', 'medium.com', 'blog'
                    ]):
                        sources.append({
                            'url': url,
                            'title': r.get('title', ''),
                            'snippet': r.get('body', '')
                        })
            
            return {
                'ceo_name': ceo_name,
                'mention_count': total_mentions,
                'credible_sources': len(sources),
                'sources': sources[:5]  # Top 5 sources
            }
    except Exception as e:
        print(f"Error validating CEO candidate: {e}")
        return {
            'ceo_name': ceo_name,
            'mention_count': 0,
            'credible_sources': 0,
            'sources': []
        }

# Tool: Scrape website homepage
def scrape_homepage(website_url: str) -> str:
    """Scrape the homepage of a website and return the text content.
    
    Args:
        website_url: The URL of the website to scrape
    
    Returns:
        str: The text content from the homepage
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(website_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Return first 2000 characters
        return text_content[:2000]
    except Exception as e:
        print(f"Error scraping website: {e}")
        return ""

# Agent 1: Find website link and extract URL
website_finder_agent = Agent(
    model=model,
    name='website_finder_agent',
    description='Finds the official company website URL using search and extracts just the URL.',
    instruction='''You are a website finder agent. When given a company name, search for the official website and return ONLY the URL.

Your output must be ONLY the URL, nothing else. For example:
https://stripe.com

Do not include any explanation, text, or JSON formatting. Just the URL.''',
    tools=[search_company_website],
    output_key=STATE_WEBSITE_URL,
)

# Agent for individual social media platform (searches and cleans)
def create_social_platform_agent(platform_name: str) -> Agent:
    """Create an agent that searches and cleans links for a specific social media platform."""
    return Agent(
        model=model,
        name=f'social_{platform_name}_agent',
        description=f'Searches for {platform_name} links, gets top 3 results, and uses LLM to identify the correct official link.',
        instruction=f'''You are a {platform_name} link finder. Your task is to find the official {platform_name} profile for the company.

Extract the company name from the user's original input. The company website URL (if available) is: {{website_url}}

Step 1: Use the search_social_platform tool with:
- company_name: extracted from user input
- platform: "{platform_name}"
- website: {{website_url}} (if available)

Step 2: From the top 3 results returned, identify the official/correct {platform_name} link.

Return ONLY the URL string if found, or "null" if no valid link is found. Do not return JSON, just the URL or "null".

Example output:
https://linkedin.com/company/example

or

null''',
        tools=[search_social_platform],
        output_key=f'social_{platform_name}_url',
    )

# Create agents for each platform
linkedin_agent = create_social_platform_agent("linkedin")
twitter_agent = create_social_platform_agent("twitter")

# Agent 2: LoopAgent for social links (loops through each platform, max_iterations=4)
social_links_loop_agent = LoopAgent(
    name='social_links_loop_agent',
    description='Loops through each social media platform (LinkedIn, Twitter) to find and clean links.',
    sub_agents=[linkedin_agent, twitter_agent],
    max_iterations=2,
)

# Agent to combine individual social platform results into JSON
social_links_combiner_agent = Agent(
    model=model,
    name='social_links_combiner_agent',
    description='Combines individual social media platform results into a single JSON object.',
    instruction='''You are a social links combiner. Combine the individual social media platform results into a single JSON object.

You have access to:
- LinkedIn URL: {{social_linkedin_url}}
- Twitter URL: {{social_twitter_url}}

Return ONLY a valid JSON object with this exact structure:
{
  "linkedin": "url or null",
  "twitter": "url or null",
}

If a value is "null" (string), convert it to null (JSON null). Return ONLY the JSON, no other text.''',
    output_key=STATE_SOCIAL_LINKS,
)

# Agent 3a: CEO Candidates Fetcher Agent
ceo_candidates_agent = Agent(
    model=model,
    name='ceo_candidates_agent',
    description='Fetches top 3 CEO candidates for a company.',
    instruction='''You are a CEO candidates fetcher. Your task is to find the top 3 CEO candidates for a company.

Extract the company name from the user's original input. The company website URL is: {{website_url}}

Use the search_ceo_candidates tool with the company name and website URL to get top 3 CEO candidates.

From the search results, extract the CEO names. Return a JSON array with exactly 3 CEO candidate names (or fewer if less are found).

Example output:
["John Smith", "Jane Doe", "Bob Johnson"]

Return ONLY the JSON array, no other text. If no candidates found, return [].''',
    tools=[search_ceo_candidates],
    output_key=STATE_CEO_CANDIDATES,
)

# Agent for validating individual CEO candidate (inside loop)
def create_ceo_validation_agent(candidate_index: int) -> Agent:
    """Create an agent that validates a specific CEO candidate."""
    return Agent(
        model=model,
        name=f'ceo_validation_agent_{candidate_index}',
        description=f'Validates CEO candidate #{candidate_index + 1} by searching for mentions with the company.',
        instruction=f'''You are a CEO validation agent. Your task is to validate CEO candidate #{candidate_index + 1} by searching for mentions of this person with the company.

Extract the company name from the user's original input. The CEO candidates list is: {{ceo_candidates}}

**Step 1: Extract the candidate**
The candidates list is a JSON array. Extract the candidate at index {candidate_index} (0-indexed, so index 0 is first candidate, index 1 is second, index 2 is third).

**Step 2: Validate the candidate**
Use the validate_ceo_candidate tool with:
- ceo_name: the candidate name you extracted from index {candidate_index}
- company_name: extracted from user input

The tool will search for mentions of this CEO candidate with the company on social media (LinkedIn, Twitter) and blogs.

**Step 3: Return validation results**
Return a JSON object with the validation results:
{{
  "ceo_name": "candidate name",
  "mention_count": number from tool result,
  "credible_sources": number from tool result,
  "validation_score": number (calculate as: mention_count * 2 + credible_sources * 3)
}}

Return ONLY the JSON object, no other text.''',
        tools=[validate_ceo_candidate],
        output_key=f'ceo_validation_{candidate_index}',
    )

# Create validation agents for top 3 candidates
ceo_validation_agent_0 = create_ceo_validation_agent(0)
ceo_validation_agent_1 = create_ceo_validation_agent(1)
ceo_validation_agent_2 = create_ceo_validation_agent(2)

# Agent 3b: LoopAgent for CEO validation (loops through each candidate, max_iterations=3)
ceo_validation_loop_agent = LoopAgent(
    name='ceo_validation_loop_agent',
    description='Loops through each CEO candidate to validate them by searching for mentions with the company.',
    sub_agents=[ceo_validation_agent_0, ceo_validation_agent_1, ceo_validation_agent_2],
    max_iterations=3,
)

# Agent 3c: CEO Selector Agent (after validation loop)
ceo_selector_agent = Agent(
    model=model,
    name='ceo_selector_agent',
    description='Selects the CEO candidate with highest validation score (most mentions with company).',
    instruction='''You are a CEO selector agent. Your task is to select the CEO candidate with the highest probability based on validation results.

You have access to:
- CEO validation results: {{ceo_validation_0}}, {{ceo_validation_1}}, {{ceo_validation_2}}

**Your Task:**
1. Review all validation results
2. For each candidate, calculate or use the validation_score (mention_count * 2 + credible_sources * 3)
3. Select the candidate with the HIGHEST validation_score
4. If multiple candidates have similar scores, prefer the one with more credible_sources

**Output:**
Return ONLY the CEO name (e.g., "John Smith") of the candidate with highest validation score, or "null" if no valid candidate found. Do not include explanations or JSON formatting.''',
    output_key=STATE_CEO_INFO,
)

# Agent 4: Scrape website for company summary
website_summary_agent = Agent(
    model=model,
    name='website_summary_agent',
    description='Scrapes the website homepage and creates a short summary of what the company does.',
    instruction='''You are a website summarizer. Scrape the company website homepage and create a short summary (2-3 sentences) about what the company does.

The website URL is: {{website_url}}

Use the scrape_homepage tool with the website URL to get the website content, then create a concise summary.

Your output must be ONLY the summary text, nothing else. Keep it to 2-3 sentences.''',
    tools=[scrape_homepage],
    output_key=STATE_COMPANY_SUMMARY,
)

# Final output agent: Combines all results into JSON
final_output_agent = Agent(
    model=model,
    name='final_output_agent',
    description='Combines all collected information into a final JSON output.',
    instruction='''You are a final output formatter. Combine all the collected information into a strict JSON format.

You have access to:
- Website URL: {{website_url}}
- Social Links: {{social_links}}
- CEO Info: {{ceo_info}}
- Company Summary: {{company_summary}}

Return ONLY a valid JSON object with this exact structure:
{
  "company_website": "string",
  "social_profile_links": {
    "linkedin": "string or null",
    "twitter": "string or null"
  },
  "company_ceo": "string or null",
  "company_summary": "string"
}

Return ONLY the JSON object, no other text, no markdown formatting, just pure JSON.''',
    output_key='final_result',
)

# Root agent: Sequential workflow
root_agent = SequentialAgent(
    name='root_agent',
    description='Orchestrates the data enrichment workflow: find website, social links, CEO info, and company summary.',
    sub_agents=[
        website_finder_agent,
        social_links_loop_agent,
        social_links_combiner_agent,
        ceo_candidates_agent,
        ceo_validation_loop_agent,
        ceo_selector_agent,
        website_summary_agent,
        final_output_agent,
    ],
)
