import requests
import os
import json
from bs4 import BeautifulSoup
import time
import pandas as pd
from collections import Counter
import networkx as nx
from itertools import combinations
import html
import unicodedata

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


#starting network analysis
import re
import unicodedata

def clean_keyword(keyword):
    keyword = str(keyword)
    keyword = html.unescape(keyword) #was getting keywords with html attached
    keyword = unicodedata.normalize("NFKC", keyword) #normalize unicode
    keyword = keyword.strip() #remove white space
    keyword = keyword.casefold()
    keyword = re.sub(r"\s+", " ", keyword)
    if not re.search(r"[a-zA-Z0-9]", keyword):
        return None
    return keyword

# Clean keywords for every paper
df["clean_keywords"] = df["keywords"].apply(
    lambda keywords: list(
        set(cleaned for cleaned in (clean_keyword(k) for k in keywords)
            if cleaned is not None)))


# Basic keyword statistics
papers_with_keywords = df[
    df["clean_keywords"].apply(len) > 0
]

papers_with_2plus_keywords = df[
    df["clean_keywords"].apply(len) >= 2
]

print("Total papers:", len(df))
print("Papers with keywords:", len(papers_with_keywords))
print(
    "Papers with 2+ keywords:",
    len(papers_with_2plus_keywords)
)

print(
    "Papers without enough keywords to form an edge:",
    len(df) - len(papers_with_2plus_keywords)
)


# Count total and unique cleaned keywords

all_keywords = [
    keyword
    for keyword_list in df["clean_keywords"]
    for keyword in keyword_list
]

print("Total keyword occurrences:", len(all_keywords))
print("Unique keywords:", len(set(all_keywords)))
keyword_counts = Counter(all_keywords)

print("\nTop 20 keywords:")
for keyword, count in keyword_counts.most_common(20):
    print(f"{keyword}: {count}")
'''
From this outut: 878 papers have at least one author keyword,877 papers have at least two keywords, 123 papers have no author keywords, 4589 keywords occurences, 3600 unique cleaned keywords.
'''

#start the graph
# Create an undirected graph
G = nx.Graph()
#clean and remove duplicate keywords
for keywords in df["clean_keywords"]:

    # Remove duplicate keywords within the same paper
    keywords = sorted(set(keywords))

    # Add keywords as nodes
    G.add_nodes_from(keywords)

    # Connect every pair of keywords in the same paper
    for topic1, topic2 in combinations(keywords, 2):

        # if this pair already exists, increase its weight
        if G.has_edge(topic1, topic2):
            G[topic1][topic2]["weight"] += 1
        else:
            G.add_edge(topic1, topic2, weight=1)

print("Number of nodes:", G.number_of_nodes())
print("Number of edges:", G.number_of_edges())
# Degree = number of distinct topics directly connected
degree = dict(G.degree())

# Degree centrality = normalized degree
degree_centrality = nx.degree_centrality(G)

# Build results table
centrality_df = pd.DataFrame({
    "topic": list(G.nodes()),
    "degree": [degree[node] for node in G.nodes()],
    "degree_centrality": [
        degree_centrality[node]
        for node in G.nodes()
    ]
})
topic_paper_count = Counter()

for keywords in df["clean_keywords"]:
    for topic in set(keywords):
        topic_paper_count[topic] += 1

centrality_df["paper_count"] = centrality_df["topic"].map(
    topic_paper_count
)

# Sort by degree centrality
centrality_df = centrality_df.sort_values(
    "degree_centrality",
    ascending=False
)

print(
    centrality_df[
        ["topic", "degree", "degree_centrality", "paper_count"]
    ].head(20).to_string(index=False)
)
'''
Okay so we now see that the top topics are mental health, gender, race, covid-19, and machine learning. but why? lets see what is sitting around each node.
'''
top_topics = [
    "mental health",
    "covid-19",
    "race",
    "gender",
    "machine learning"
]

for topic in top_topics:
    print(f"\n{topic.upper()}")
    

    neighbors = list(G.neighbors(topic))

    print("Number of connections:", len(neighbors))
    print("Connected topics:")

    for neighbor in sorted(neighbors):
        weight = G[topic][neighbor]["weight"]
        print(f"  {neighbor}  (co-occurrences: {weight})")
#lets also check if the centrality is valid. ex: one paper isnt inflating the degree. (it happened last time)

for topic in top_topics:

    print(f"\n{topic.upper()}")

    neighbors_with_weights = [
        (neighbor, G[topic][neighbor]["weight"])
        for neighbor in G.neighbors(topic)
    ]

    neighbors_with_weights.sort(
        key=lambda x: x[1],
        reverse=True
    )

    print("Top 10 strongest connections:")

    for neighbor, weight in neighbors_with_weights[:10]:
        print(f"{neighbor}: {weight}")

#graph visualization
# Export graph for Gephi
nx.write_graphml(
    G,
    "umd_research_topics.graphml"
)

# Export centrality results
centrality_df.to_csv(
    "umd_topic_centrality.csv",
    index=False
)

print("Graph saved: umd_research_topics.graphml")
print("Centrality table saved: umd_topic_centrality.csv")