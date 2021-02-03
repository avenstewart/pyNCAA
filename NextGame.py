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


def search_year_schedule():
    week_ids = {}
    url = "https://fbschedules.com/college-football-schedule/"
    init_html = get_resp_from_url(url, "html")
    weeks_options = init_html.find("select", {'name': 'select-week-menu'}).findAll("option")
    for option in weeks_options:
        week_info = get_week_info(option['value'])
        week_ids[option.text.split(" ")[1]] = week_info
        if contains_next_game(week_info):
            next_game_obj = get_next_game_from_week_obj(week_info)
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


def get_week_info(week_id):
    week_info = OrderedDict()
    cur_year = current_date.strftime("%Y")
    url = ("https://fbschedules.com/wp-admin/admin-ajax.php?action=load_fbschedules_ajax&type=NCAA&" \
               "display=current&team=&current_season=%s&view=weekly&conference=&conference-division=&" \
               "ncaa-subdivision=fbs&ispreseason=&current-page-type=&is_spring_week_only=&pid=45221&" \
               "schedule-week=%s" % (cur_year, week_id))
    week_raw = get_resp_from_url(url, "json")["html"]
    week_raw = bsoup(week_raw.replace(r"\"", '"').replace(r"\/", "/").replace(r"\n", ""), "html.parser")
    week_dates = get_week_dates_objs_from_raw(week_raw, cur_year)
    game_table_set = [tdate.find("tbody") for tdate in week_raw.findAll("table", {"class":"spring"})]
    for ndx, gdate in enumerate(game_table_set):
        games_lol = extract_gamestr_from_tbody(gdate)
        week_info[week_dates[ndx]] = games_lol

    return week_info


def extract_gamestr_from_tbody(tbody):
    games_lol = []
    tr_list = tbody.findAll("tr")
    for game in tr_list:
        game_teams = game.find("span").text
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
    return datetime.strptime(cur_year+" "+date_str, '%Y %A, %B %d')


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


def get_next_game_from_week_obj(week_info):
    final_game = 0
    dates_list = list(week_info.keys())
    todays_date = current_date.date()
    day_count = 0
    while day_count < len(dates_list):
        if dates_list[day_count].date() < todays_date:
            day_count += 1
        else:
            games_list = list(week_info.values())
            for game in games_list[day_count]:
                if game[1] == "Time TBA":
                    game.append(dates_list[day_count].date())
                    final_game = game
                elif parse_textual_time(game[1]) > current_time:  # should be ET in format %I:%M%p
                    game.append(dates_list[day_count].date())
                    return game
            day_count += 1
    return final_game


def pretty_print_game_obj(game):
    print("The next NCAA game of the %s season happens on:\n" % datetime.now().year)
    print("%s\n%s\nTime: %s (%s)\nTV airtime: %s\nBuy Tickets:%s\n" %
            (game[4], game[0], game[1], timezone_str, game[2], game[3]))


output = search_year_schedule()
if len(output) != 0:
    pretty_print_game_obj(search_year_schedule())
else:
    print("There are no more upcoming games for this season, sorry!")
