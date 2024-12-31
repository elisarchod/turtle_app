import requests
from bs4 import BeautifulSoup

# URL of the API documentation
url = "https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)"

# Fetch the page content
response = requests.get(url)

if response.status_code == 200:
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the main content (or modify based on the structure of the page)
    main_content = soup.find(id="wiki-content")  # Adjust based on GitHub Wiki layout

    if main_content:
        # Get plain text or save HTML
        text = main_content.get_text(strip=True)

        # Save to a file
        with open("qbittorrent_api_documentation.txt", "w", encoding="utf-8") as file:
            file.write(text)

        print("Documentation saved successfully!")
    else:
        print("Could not find the main content on the page.")
else:
    print(f"Failed to fetch the page. Status code: {response.status_code}")
