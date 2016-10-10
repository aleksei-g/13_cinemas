import requests
from bs4 import BeautifulSoup
import re
import argparse
import sys


URL_AFISHA_PAGE = 'http://www.afisha.ru/msk/schedule_cinema/'
URL_KINOPOISK_SEARCH = 'https://www.kinopoisk.ru/index.php'


def create_parser():
    parser = argparse.ArgumentParser(description='Скрипт выводит самые \
                                     популярные фильмы, идущие в данный \
                                     момент, отсортированные по рейтингу.')
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
    response.encoding = 'utf-8'
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
        movies.append({'movie': movie, 'cinemas_count': cinemas_count})
    return movies


def fetch_movie_info(page):
    if page is None:
        return {'rating': 0, 'voices': 0}
    soup = BeautifulSoup(page, 'lxml')
    element_most_wanted = \
        soup.find('div', {'class': 'element most_wanted'})
    if element_most_wanted:
        elem_rating_and_voices = \
            element_most_wanted.find(
                                     'div',
                                     {'class': re.compile(r'rating .*')}
                                     )
        if elem_rating_and_voices:
            rating_and_voices = elem_rating_and_voices.get('title')
            rating = elem_rating_and_voices.text
            voices = re.search(
                               r'(?<= \().*(?=\))',
                               rating_and_voices
                               ).group()
            voices = voices.replace(' ', '')
            return {'rating': rating, 'voices': voices}
    return {'rating': 0, 'voices': 0}


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
    for movie in movies:
        movie.update(fetch_movie_info(
           fetch_site_page(url=URL_KINOPOISK_SEARCH,
                           payload={'kp_query': movie['movie']})))
    output_movies_to_console(movies, namespace.top, namespace.cinemas)
