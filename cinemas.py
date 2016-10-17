import requests
from bs4 import BeautifulSoup
import re
import argparse
import sys
from multiprocessing import Pool


URL_AFISHA_PAGE = 'http://www.afisha.ru/msk/schedule_cinema/'
URL_KINOPOISK_SEARCH = 'https://www.kinopoisk.ru/index.php'
POOL_COUNT = 4


def create_parser():
    parser = argparse.ArgumentParser(description="Скрипт выводит самые \
                                     популярные фильмы, идущие в данный \
                                     момент, отсортированные по рейтингу.")
    parser.add_argument('-t', '--top', metavar='ТОП', type=int, default=10,
                        help='Размер топ-списка фильмов.')
    parser.add_argument('-c', '--cinemas', metavar='КИРОТЕАТРЫ', type=int,
                        default=None,
                        help='Минимальное количество кинотеатров, \
                        в которых идет показ фильма.')
    return parser


def fetch_site_page(url, payload=None):
    try:
        response = requests.get(url, params=payload, timeout=(10, 10))
    except requests.exceptions.RequestException:
        return None
    return response.text


def parse_afisha_list(page):
    soup = BeautifulSoup(page, 'lxml')
    movies = []
    movies_and_cinemas = \
        soup.findAll(
                     'div',
                     {'class': 'object s-votes-hover-area collapsed'}
                     )
    for movie_and_cinemas in movies_and_cinemas:
        movie = movie_and_cinemas.find('h3', {'class': 'usetags'}).text
        cinemas_count = \
            len(movie_and_cinemas.findAll('td', {'class': 'b-td-item'}))
        movies.append([movie, cinemas_count])
    return movies


def fetch_movie_info(page):
    soup = BeautifulSoup(page, 'lxml')
    element_most_wanted = \
        soup.find('div', {'class': 'element most_wanted'})
    if not element_most_wanted:
        return None
    elem_rating_and_voices = \
        element_most_wanted.find('div', {'class': re.compile(r'rating .*')})
    if not elem_rating_and_voices:
        return None
    rating_and_voices = elem_rating_and_voices.get('title')
    rating = elem_rating_and_voices.text
    voices = re.search(r'(?<= \().*(?=\))', rating_and_voices).group()
    voices = voices.replace(' ', '')
    return [rating,  voices]


def get_movie_rating(movie):
    kinopoisk_page = fetch_site_page(url=URL_KINOPOISK_SEARCH,
                                     payload={'kp_query': movie})
    if not kinopoisk_page:
        return [0, 0]
    movie_rating = fetch_movie_info(kinopoisk_page)
    if not movie_rating:
        return [0, 0]
    return movie_rating


def update_movie_info_from_kinopoisk(movie):
    movie_rating = get_movie_rating(movie[0])
    return {'movie': movie[0],
            'cinemas_count': movie[1],
            'rating': movie_rating[0],
            'voices': movie_rating[1]
            }


def update_movies_info_from_kinopoisk(movies):
    pool = Pool(POOL_COUNT)
    movies = pool.map(update_movie_info_from_kinopoisk, movies)
    pool.close()
    pool.join()
    return movies


def output_movies_to_console(movies, top_size=10, cinemas_over=None):
    movies.sort(key=lambda d: float(d['rating']), reverse=True)
    if cinemas_over:
        movies = list(filter(lambda d: d['cinemas_count'] >= cinemas_over,
                             movies))
    print('{0:^3} {1:<40} {2:>10} {3:>10} {4:>10} '
          .format('№', 'ФИЛЬМ', 'РЕЙТИНГ', 'ГОЛОСА', 'КИНОТЕАТРЫ'))
    print()
    for num, movie in enumerate(movies[:top_size], start=1):
        print('{0:0>3} {1:<40} {2:>10} {3:>10} {4:>10} '.format(
                      '%s.' % num, movie['movie'], movie['rating'],
                      movie['voices'], movie['cinemas_count']))


if __name__ == '__main__':
    parser = create_parser()
    namespace = parser.parse_args()
    afisha_page = fetch_site_page(url=URL_AFISHA_PAGE)
    if afisha_page is None:
        print('%s недоступен.' % URL_AFISHA_PAGE)
        sys.exit(1)
    movies = parse_afisha_list(afisha_page)
    movies = update_movies_info_from_kinopoisk(movies)
    output_movies_to_console(movies, namespace.top, namespace.cinemas)
