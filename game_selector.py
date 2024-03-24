import os
import re
import requests
import datetime
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


def get_steam_reviews(game_title):
    search_url = f'https://store.steampowered.com/search/?term={game_title}'
    game_data = {}
    game_data["game"] = game_title

    response = requests.get(search_url)

    soup = BeautifulSoup(response.text, 'html.parser')

    search_results_div = soup.find('div', id='search_resultsRows')

    if search_results_div is None:
        return game_data

    url = search_results_div.find('a')['href']

    if url is None:
        return game_data
    
    parts = url.split("/", 5)
    refine_url = "/".join(parts[:5])

    if refine_url:
        game_data["url"] = refine_url

    review_element = soup.find('span', {'class': 'search_review_summary positive'})
    
    if review_element is None:
        return game_data

    content = review_element['data-tooltip-html']

    if content is None:
        return game_data

    match = re.search(r'(\d+)%.*?(\d+(?:,\d+)*)', content)

    if match:
        rate = match.group(1)
        review = match.group(2)
        game_data["rate"] = rate
        game_data["review"] = review
        return game_data
    else:
        return game_data


def load_game_list(game_list_path):
    with open(game_list_path, "r", encoding="utf-8") as file:
        game_list = [line.strip() for line in file]

    return game_list


def crawl_game_reviews(game_list, max_workers=10):
    results = []

    def update_progress(future):
        pbar.update(1)
        pbar.set_postfix(result=future.result()['game'])

    with ThreadPoolExecutor(max_workers=max_workers) as executor, tqdm(total=len(game_list), desc="Crawl progress") as pbar:
        futures = [executor.submit(get_steam_reviews, game_title) for game_title in game_list]

        for future in futures:
            if future:
                future.add_done_callback(lambda x: update_progress(x))
            else:
                future.add_done_callback(update_progress())

        results = [future.result() for future in futures]

    return pd.DataFrame(results)


def main():
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    file_path = os.path.dirname(os.path.abspath(__file__))
    
    game_list_path = os.path.join(file_path, 'game_list.txt')
    
    # game_list = load_game_list(game_list_path)

    game_list = ["Grim Dawn", "Venba"]

    output_folder = os.path.join(file_path, "output")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    output_file = os.path.join(output_folder, f"result_{current_time}.xlsx")

    crawl_game_reviews(game_list).to_excel(output_file, index=False, header=True)


if __name__ == "__main__":
    main()