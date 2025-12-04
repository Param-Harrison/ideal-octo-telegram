# Data enrichment multi-agent system

- Input: https://stripe.com or short data about the company with name and website
- Output: JSON object with company details
-- Company name
-- Company website
-- Company description
-- Company industry
-- Company size
-- Company location
-- Company revenue
-- Company employees
-- Company founded year
-- Company CEO
-- Company CTO
-- Company CFO
-- Company Services & Products
-- Social profile links (LinkedIn, Twitter, Facebook, Instagram, etc.)
-- Three closest competitors

## How doess the agent collects the data?

- Google search (using duckduckgo-search)
- Social media search (LinkedIn, Twitter, Facebook, Instagram, etc.)
- Searching their services and products
- Using the services/products to find competitng companies (multi-search)
- Evaluate whether those competitors are actually competitors ????
--- Three closest competitors for each service/product ????

## Google ADK

## Designing the agents

1. Pure LLM Agent (root_agent)

- Hallucinating reponse from LLM

2. Multiple Agents with search tools

- Social link search (LinkedIn, Twitter, Facebook, Instagram, etc.)
- Search the website, scrape data and create summary along with company information. Also create a list of services and products.
- Key people search (CEO, CTO, CFO, etc.)
- Competitors search (multi-search) ????