import requests
import os
import json
from bs4 import BeautifulSoup
import time
import pandas as pd
from collections import Counter

#web of science api key
API_KEY = os.environ.get('WOS_API_KEY')
# Web of Science API endpoint
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
headers = {
    "X-ApiKey": API_KEY,
    "Accept": "application/json"
}
all_papers=[]

'''# Test query
query = 'TS=(machine learning)'

params = {
    "db": "WOS",
    "q": "OG=(University of Maryland, College Park)",
    "limit": 5,
    "page": 1
}

headers = {
    "X-ApiKey": API_KEY,
    "Accept": "application/json"
}

response = requests.get(
    BASE_URL,
    params=params,
    headers=headers
)

print("Status code:", response.status_code)

if response.ok:
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print("Error:")
    print(response.text)
'''
# Collect 200 publications from each year

for year in range(2021, 2026):

    query = (
        'OG=("University of Maryland, College Park") '
        f'AND PY={year} '
        'AND DT=(Article OR Review)'
    )

    print(f"\nCollecting {year}...")

    for page in range(1, 5):  # 4 pages × 50 = 200

        params = {
            "db": "WOS",
            "q": query,
            "limit": 50,
            "page": page
        }

        response = requests.get(
            BASE_URL,
            params=params,
            headers=headers
        )

        print(f"  Page {page}: Status {response.status_code}")

        if not response.ok:
            print(response.text)
            break

        data = response.json()

        for paper in data["hits"]:

            authors = paper.get(
                "names", {}
            ).get(
                "authors", []
            )

            author_names = [
                author.get("displayName")
                for author in authors
            ]

            keywords = paper.get(
                "keywords", {}
            ).get(
                "authorKeywords", []
            )

            all_papers.append({
                "uid": paper.get("uid"),
                "title": paper.get("title"),
                "year": paper.get(
                    "source", {}
                ).get("publishYear"),
                "authors": author_names,
                "keywords": keywords
            })

        time.sleep(0.5)

print("\nTotal papers collected:", len(all_papers))

df = pd.DataFrame(all_papers)

# Save the dataset
df.to_csv("umd_wos_publications_2021_2025.csv", index=False)

print("Saved to umd_wos_publications_2021_2025.csv")
#verify
print("Total papers:", len(df))
print("Earliest year:", df["year"].min())
print("Latest year:", df["year"].max())

print("\nPapers by year:")
print(df["year"].value_counts().sort_index())
'''

# Convert to DataFrame
df = pd.DataFrame(all_papers)

# Save dataset
df.to_csv("umd_wos_publications.csv", index=False)
print("Total papers:", len(df))
print("Earliest year:", df["year"].min())
print("Latest year:", df["year"].max())

print("\nPapers by year:")
print(df["year"].value_counts().sort_index())
print("Saved publications to csv file.")
Extracting basic information
        uid = paper.get("uid")
        title = paper.get("title")
        year = paper.get("source", {}).get("publishYear")

        #Extracting author names
        authors = paper.get("names", {}).get("authors", [])
        author_names = [
            author.get("displayName")
            for author in authors
        ]

        #Extracting author keywords
        keywords = paper.get("keywords", {}).get("authorKeywords", [])

        #put information in a dictionary for better search
        all_papers.append({
            "uid": uid,
            "title": title,
            "year": year,
            "authors": author_names,
            "keywords": keywords
        })

    # Small pause between requests. To avoid rate limiting.
    

print()
print("Total papers collected:", len(all_papers))

# Convert to DataFrame
df = pd.DataFrame(all_papers)
#print first 5 papers and info
print(df.head())
df.to_csv("umd_wos_publications.csv", index=False)
print("Saved publications to csv file.")
print("Total papers:", len(df))
print("Earliest year:", df["year"].min())
print("Latest year:", df["year"].max())

print("\nPapers by year:")
print(df["year"].value_counts().sort_index())

- now we have all our data in a csv file.
- I queried WOS for publications at UMD and restricted pubs to 2021-2025 and articles and reviews only. Stored each pub UID so they can be traced back to the WOS. Used author keywords to construct a research-topic network.
- next, I need to use this data and networkx mod to calculate centrality and 3 most connected research topics.
- key note: I am using a subset of the UMD research data (1000 pubs) so in my final findings, I should emphasize this sample.

import re
import unicodedata

def clean_keyword(keyword):
    # Convert to string
    keyword = str(keyword)

    # Normalize Unicode characters
    keyword = unicodedata.normalize("NFKC", keyword)

    # Remove leading/trailing whitespace
    keyword = keyword.strip()

    # Convert everything to lowercase
    keyword = keyword.casefold()

    # Replace repeated whitespace with a single space
    keyword = re.sub(r"\s+", " ", keyword)

    return keyword


# Apply cleaning to every paper's keyword list
df["clean_keywords"] = df["keywords"].apply(
    lambda keywords: list(set(clean_keyword(k) for k in keywords))
)

# Show some examples
print(df[["keywords", "clean_keywords"]].head(10))

raw_keywords = {
    keyword
    for keyword_list in df["keywords"]
    for keyword in keyword_list
}

cleaned_keywords = {
    keyword
    for keyword_list in df["clean_keywords"]
    for keyword in keyword_list
}

#figured out a limitation: 
# only 3 keyword-containing papers are unable to produce an edge because they have exactly one keyword. The other 344 papers have no author keywords at all.
import networkx as nx
from itertools import combinations

# Create an undirected graph
G = nx.Graph()

for keywords in df["clean_keywords"]:

    # Remove duplicate keywords within a paper
    keywords = sorted(set(keywords))

    # Add each keyword as a node
    G.add_nodes_from(keywords)

    # Create an edge between every pair of keywords
    # that appears in the same paper
    for keyword1, keyword2 in combinations(keywords, 2):
        G.add_edge(keyword1, keyword2)

print("Number of nodes:", G.number_of_nodes())
print("Number of edges:", G.number_of_edges())
# Calculate degree centrality
degree_centrality = nx.degree_centrality(G)

# Calculate raw degree
degree = dict(G.degree())

# Create a table
centrality_df = pd.DataFrame({
    "topic": list(G.nodes()),
    "degree": [degree[node] for node in G.nodes()],
    "degree_centrality": [
        degree_centrality[node]
        for node in G.nodes()
    ]
})

# Sort by degree centrality
centrality_df = centrality_df.sort_values(
    "degree_centrality",
    ascending=False
)

#print(centrality_df.head(20).to_string(index=False))
    
    3,173 nodes and 9,550 edges.
    most connected topics: noise, topology, climate change. 
    are 'noise' and 'topology' actually highly connected accross UMD research or are they being driven by a small number of papers?
    
#compare centrality with publication frequency
# Count how many different papers contain each topic
topic_paper_count = Counter()

for keywords in df["clean_keywords"]:
    for keyword in set(keywords):
        topic_paper_count[keyword] += 1

# Add paper frequency to the centrality dataframe
centrality_df["paper_count"] = centrality_df["topic"].map(topic_paper_count)

print(
    centrality_df[
        ["topic", "degree", "degree_centrality", "paper_count"]
    ].head(20).to_string(index=False)
)
# Most frequently appearing topics
frequency_df = (
    centrality_df[
        ["topic", "paper_count", "degree", "degree_centrality"]
    ]
    .sort_values("paper_count", ascending=False)
)

print(frequency_df.head(20).to_string(index=False))

I also noticed that 3,170 cleaned unique keywords does not equal 3,173 nodes but it should. maybe check the 3 extra keywords?

all_clean_keywords = {
    keyword
    for keyword_list in df["clean_keywords"]
    for keyword in keyword_list
}

print("Unique keywords in dataframe:", len(all_clean_keywords))
print("Nodes in graph:", G.number_of_nodes())

extra_nodes = set(G.nodes()) - all_clean_keywords

print("Extra graph nodes:", extra_nodes)
#why is topology and noise at the top
top_topics = ["noise", "topology", "climate change"]

for topic in top_topics:
    print("\n" + "=" * 70)
    print(f"TOPIC: {topic}")
    print("=" * 70)

    # Papers containing this topic
    matching_papers = df[
        df["clean_keywords"].apply(
            lambda keywords: topic in keywords
        )
    ]

    print(f"Papers containing '{topic}': {len(matching_papers)}")

    for _, paper in matching_papers.iterrows():
        print("\nTitle:", paper["title"])
        print("Year:", paper["year"])
        print("Keywords:", paper["clean_keywords"])
# is my network dominated by a lot of disconnected clusters?
# Basic network statistics

num_nodes = G.number_of_nodes()
num_edges = G.number_of_edges()

average_degree = (2 * num_edges) / num_nodes

components = list(nx.connected_components(G))

print("Nodes:", num_nodes)
print("Edges:", num_edges)
print(f"Average degree: {average_degree:.2f}")
print("Connected components:", len(components))

largest_component = max(components, key=len)

print(
    "Largest connected component:",
    len(largest_component),
    "nodes"
)
'''