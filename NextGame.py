import contextlib
import urllib.request
import bs4 as bs
import json
import pytz
from datetime import datetime
from collections import OrderedDict
from time import sleep

bsoup = bs.BeautifulSoup
current_date = datetime.now()
timezone_str = "US/Central"
our_timezone = pytz.timezone(timezone_str)
current_time = our_timezone.localize(current_date)
timezone_of_API = pytz.timezone('US/Eastern')


def search_year_schedule():
    week_ids = {}
    url = "https://fbschedules.com/college-football-schedule/"
    init_html = get_resp_from_url(url, "html")
    weeks_options = init_html.find("select", {'name': 'select-week-menu'}).findAll("option")

    for option in weeks_options:
        all_games_for_week = scrape_week_info_from_web_page(option['value'])
        week_ids[option.text.split(" ")[1]] = all_games_for_week
        # check if this is the current week
        if contains_next_game(all_games_for_week):
            # testing
            # I don't know enough about how this list works that there needs to be a [0] here.
            # Something to learn about later. I think it's because it's for the [0] date.
            # If other dates were in it, I guess they'd be at other indexes
            return list(all_games_for_week.values())[0]
            # Need to revisit purpose of this. This seems to be more formatting?
            # But not sure if there needs to be formatting?
            # next_game_obj = get_next_game_from_week_obj_test(all_games_for_week)
            # if next_game_obj != 0:
            # return next_game_obj
    return 0


def get_one_week_of_games():
    week_ids = {}
    url = "https://fbschedules.com/college-football-schedule/"
    init_html = get_resp_from_url(url, "html")
    weeks_options = init_html.find("select", {'name': 'select-week-menu'}).findAll("option")

    for option in weeks_options:
        all_games_for_week = scrape_week_info_from_web_page(option['value'])
        week_ids[option.text.split(" ")[1]] = all_games_for_week
        if contains_next_game(all_games_for_week):
            # testing
            # I don't know enough about how this list works that there needs to be a [0] here.
            # Something to learn about later. I think it's because it's for the [0] date.
            # If other dates were in it, I guess they'd be at other indexes
            next_game_obj = get_next_game_from_week_obj_test(all_games_for_week)
            if next_game_obj != 0:
                return next_game_obj
    return 0


def contains_next_game(week_info):
    dates_list = list(week_info.keys())
    todays_date = current_date.date()
    day_count = 0
    while day_count < len(dates_list):
        if dates_list[day_count].date() < todays_date:
            day_count += 1
        else:
            return True
    return False


def scrape_week_info_from_web_page(week_id):
    week_info = OrderedDict()
    cur_year = current_date.strftime("%Y")
    url = ("https://fbschedules.com/wp-admin/admin-ajax.php?action=load_fbschedules_ajax&type=NCAA&"
           "display=current&team=&current_season=%s&view=weekly&conference=&conference-division=&"
           "ncaa-subdivision=fbs&ispreseason=&current-page-type=&is_spring_week_only=&pid=45221&"
           "schedule-week=%s" % (cur_year, week_id))
    week_raw = get_resp_from_url(url, "json")["html"]
    week_raw = bsoup(week_raw.replace(r"\"", '"').replace(r"\/", "/").replace(r"\n", ""), "html.parser")
    week_dates = get_week_dates_objs_from_raw(week_raw, cur_year)
    game_table_set = [tdate.find("tbody") for tdate in week_raw.findAll("table", {"class": "spring"})]
    for ndx, gdate in enumerate(game_table_set):
        games_lol = extract_gamestr_from_tbody(gdate)
        week_info[week_dates[ndx]] = games_lol
    return week_info


def extract_gamestr_from_tbody(tbody):
    games_lol = []
    tr_list = tbody.findAll("tr")
    for game in tr_list:
        # This is probably brittle and might need cleaning up
        game_team_one = game.findAll("span", class_="school-name-content")[0]
        game_team_two = game.findAll("span", class_="school-name-content")[-1]
        game_teams = str(game_team_one.text) + " vs " + str(game_team_two.text)
        # TODO tr_list[0].findAll("span", class_="team-rank") Figure out how to assign this to teams
        game_time = game.find("td", {"class": "spring2"}).text
        game_tv_date = game.find("td", {"class": "spring3"}).text
        game_tickets = game.find("td", {"class": "spring4"})
        if game_tickets.text != "":
            game_tickets = game_tickets.a["href"].split("destination:")[1]
        else:
            game_tickets = game_tickets.text
        games_lol.append([game_teams, game_time, game_tv_date, game_tickets])
    return games_lol


def parse_textual_date(date_str, cur_year):
    return datetime.strptime(cur_year + " " + date_str, '%Y %A, %B %d')


def parse_textual_time(time_str):
    eastern = pytz.timezone("US/Eastern")
    et_time_obj = eastern.localize(datetime.strptime(time_str, '%I:%M%p'))
    return et_time_obj.astimezone(our_timezone)


def get_week_dates_objs_from_raw(week_raw, cur_year):
    week_dates = [parse_textual_date(wdate.text, cur_year) for wdate in
                  week_raw.findAll("div", {"class": "bowl-year-bg"})]
    return [i for n, i in enumerate(week_dates) if i not in week_dates[:n]]


def get_resp_from_url(url, rtype):
    sleep(0.25)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla'})
    with contextlib.closing(urllib.request.urlopen(req)) as resp:
        if rtype == "json":
            return json.loads(resp.read())
        elif rtype == "html":
            return bsoup(resp.read(), "html.parser")


# Somewhere along the line this seemed to have gotten overly complicated? IDK taking a swing at simplifying
def get_next_game_from_week_obj(week_info):
    final_game = 0
    dates_list = list(week_info.keys())
    todays_date = current_date.date()
    day_count = 0
    print("DATES LIST")
    print(dates_list)
    while day_count < len(dates_list):
        if dates_list[day_count].date() < todays_date:
            day_count += 1
        else:
            games_list = list(week_info.values())
            for game in games_list[day_count]:
                game.append(dates_list[day_count].date())
                if game[1] == "Time TBA":
                    final_game = game
                elif parse_textual_time(game[1]) > current_time:  # should be ET in format %I:%M%p
                    return game
                # This is a pretty janky way to try and fix this. The issue is that the game that prints is only a
                # single game, and it's always at the very end I think if I was really going to dive into this full
                # codebase, I would put a limit of the next week and print all of them. As it is, seems like it was
                # built to only work with a week The method above that pulls the games somehow pulls about a months
                # worth else: return game
            day_count += 1
    return final_game


# ChatGPT helped so proceed with caution. Also, my python sucks. Good luck
def get_next_game_from_week_obj_test(week_info):
    dates_list = list(week_info.keys())
    todays_date = current_date.date()
    upcoming_games = []

    print("DATES LIST: " + str(dates_list))
    for date in dates_list:
        print("Single date: " + str(date))
        if date.date() >= todays_date:
            games_list = week_info[date]
            print("Game List: " + str(games_list))
            for game in games_list:
                # This is slightly overkill, however, I think we might need the full day +
                # time of day later, so I'm keeping it here. Given above check we should be on the date or later though.
                game_time = datetime.combine(date.date(), parse_textual_time(game[1]).time(), timezone_of_API)
                if game_time > current_time:
                    upcoming_games.append(game)

    return upcoming_games


# Ok my big sticking point in revisiting this is that some parts seemed ready for one game, others for multiple.
# I believe I took this and modified it to grab more games, but didn't update everything, thus the confusion
def pretty_print_game_obj(game):
    # print("The next NCAA game of the %s season happens on:" % datetime.now().year)
    # print("%s\n%s\nTime: %s (%s)\nTV airtime: %s\nBuy Tickets:%s\n" %
    #      (game[4], game[0], game[1], timezone_str, game[2], game[3]))
    print("%s\nTime: %s (%s)\nTV airtime: %s\nBuy Tickets:%s\n" %
          (game[0], game[1], timezone_of_API, game[2], game[3]))


def print_next_games(number_of_games_to_print, games):
    print("NEXT GAMES UP ARE....")
    for game in games[:number_of_games_to_print]:
        pretty_print_game_obj(game)


games_to_output = search_year_schedule()
if len(games_to_output) != 0:
    # TODO pull this number from command line
    print_next_games(10, games_to_output)
else:
    print("There are no more upcoming games for this season, sorry! Hopefully basketball is ok this year?")
