from scholar import search_papers
from db import add_papers

topic = input("Enter Research Topic: ")

papers = search_papers(topic, limit=50)

count = add_papers(papers)
print(f"Successfully processed {count} papers.")