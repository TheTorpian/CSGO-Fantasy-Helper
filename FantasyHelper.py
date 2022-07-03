import argparse, time, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta


class Team:
    def __init__(self, name):
        self.name = name


class Player:
    def __init__(self, name, price, team, rating):
        self.name = name
        self.price = price
        self.team = team
        self.rating = rating


class FantasyTeam:
    def __init__(self):
        self.picks = []
        self.price = 0
        self.total_rating = 0
        self.avg_rating = 0

    def add(self, player):
        self.picks.append(player)
        self.price += player.price
        self.total_rating += player.rating

    def drop(self):
        self.price -= self.picks[-1].price
        self.total_rating -= self.picks[-1].rating
        self.picks.pop(-1)


def add_to_lineups(team):
    t = FantasyTeam()
    for p in team.picks:
        t.add(p)
    t.avg_rating = team.total_rating / 5
    lineups.append(t)


def print_lineups():
    for l in range(len(lineups)):
        p_string = '['
        for p in lineups[l].picks:
            p_string += f'{p.name}, '
        p_string = p_string[:-2] + '] ' + f'cost: {lineups[l].price}, avg rating: {round(lineups[l].avg_rating, 2)}'
        print(f'{p_string}')


# sorting functions
def sort(s):
    match s:
        case 'price':
            lineups.sort(reverse=True, key=lambda l: l.price)
        case 'rating':
            lineups.sort(reverse=True, key=lambda l: l.avg_rating)


# returns true if trying to add more players than specified max from same team
def max_players(fantasy):
    f = []
    for p in fantasy.picks:
        f.append(p.team)
    for p in f:
        if f.count(p) > 2:
            return True
    return False


# returns true if lineup meets minimum value, false otherwise
def budget_limit(fantasy):
    if fantasy.price > min_value:
        return True
    return False


# returns true if all players from whitelist are present
def whitelist(fantasy):
    if p_whitelist:
        players_in = 0
        players_quota = len(p_whitelist)
        for p in fantasy.picks:
            if p.name in p_whitelist:
                players_in += 1
        if players_in == players_quota:
            return True  # if whitelist isn't empty and all players are in lineup
        return False  # if whitelist isn't empty and not all players are in lineup
    return True  # if whitelist is empty


# returns true if at least one player from blacklist is present in lineup, false otherwise
def blacklist(fantasy):
    if p_blacklist:
        for p in fantasy.picks:
            if p.name in p_blacklist:
                return True  # if blacklist isn't empty and at least one player is in lineup
        return False  # if blacklist isn't empty and no player is in lineup
    return False  # if whitelist is empty


# returns true if lineup conditions are met, false otherwise
def check_continue(fantasy):
    size = len(fantasy.picks)
    # see max_players()
    if max_players(fantasy):
        return False
    # discards lineup if there's a player in blacklist
    if blacklist(fantasy):
        return False
    # final checks, after getting 5 players
    if size == 5:
        #  discards lineup if price is over budget
        if fantasy.price <= 1000:
            if budget_limit(fantasy):
                # whitelist check
                if whitelist(fantasy):
                    add_to_lineups(fantasy)
        return False
    return True


def scrape():
    hltv_url = 'https://www.hltv.org'
    top30_url = f'{hltv_url}/ranking/teams/{year}/{month.lower()}/{day}'  # top 30 teams page on hltv

    results = requests.get(top30_url)
    soup = BeautifulSoup(results.text, 'html.parser')

    top30_teams = []
    all_players = []

    names_div = soup.find_all('div', class_='ranked-team standard-box')
    for container in names_div:
        t_name = container.find('span', class_='name').text  # get team name
        # rank = container.find('span', class_='position').text  # get team rank
        top30_teams.append(Team(t_name))

        # get all players from each team
        for p in container.find_all('td', class_='player-holder'):
            p_name = p.find('div', class_='nick').text  # get player name
            player_id = p.find('a', class_='pointer', href=True)['href']  # get url to player page

            # get rating from player page
            p_results = requests.get(f'{hltv_url}{player_id}')
            p_soup = BeautifulSoup(p_results.text, 'html.parser')
            time.sleep(0.4)  # hltv rate limits after too many attempts in a very short time; slows the code significantly, but it makes it work
            try:
                p_rating = p_soup.find('div', class_='playerpage-container').find('span', class_='statsVal').text
            except:
                pass

            all_players.append(Player(p_name, 0, t_name, p_rating))

    # writing to file
    with open(output_file, 'w') as f:
        f.write('[')
        for t in top30_teams[:-1]:
            f.write(f'\'{t.name}\', ')
        f.write(f'\'{top30_teams[-1].name}\']\n\n')

        for i in range(0, len(all_players)):
            current_team = all_players[i].team
            try:
                next_team = all_players[i+1].team
            except IndexError:
                pass
            f.write(f'Player(\'{all_players[i].name}\', {all_players[i].price}, \'{all_players[i].team}\', {all_players[i].rating}), ')
            if current_team != next_team:  # EoL after each team lineup for readability
                f.write('\n')


def do_lineups():
    players = []
    for p in all_players:
        if p.team in teams:
            players.append(p)

    lineup = FantasyTeam()

    length = len(players)

    for p1 in range (0, length-4):
        while len(lineup.picks) > 0:
            lineup.drop()
        lineup.add(players[p1])
        if not check_continue(lineup):
            lineup.drop()
            continue
        for p2 in range (p1+1, length-3):
            while len(lineup.picks) > 1:
                lineup.drop()
            lineup.add(players[p2])
            if not check_continue(lineup):
                lineup.drop()
                continue
            for p3 in range (p2+1, length-2):
                while len(lineup.picks) > 2:
                    lineup.drop()
                lineup.add(players[p3])
                if not check_continue(lineup):
                    lineup.drop()
                    continue
                for p4 in range (p3+1, length-1):
                    while len(lineup.picks) > 3:
                        lineup.drop()
                    lineup.add(players[p4])
                    if not check_continue(lineup):
                        lineup.drop()
                        continue
                    for p5 in range (p4+1, length):
                        lineup.add(players[p5])
                        # adds lineup if budget/whitelist is ok, return value irrelevant
                        check_continue(lineup)
                        lineup.drop()


lineups = []
all_players =[
]

# has to be global for -o option to work
# gets latest monday (update day for hltv rankings)
today = datetime.today()
day = today - timedelta(days=today.weekday())
month = day.strftime('%B')
year = today.year
day = day.strftime('%d')
output_file = f'{day}_{month.lower()}.txt'

teams = []  # teams you want players from
p_whitelist = []  # players that must be in lineup
p_blacklist = []  # players that can't be in lineup
min_value = 999  # discard lineups equal or under this value

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--scrape', action='store_true', help='scrape top30 teams/players from hltv, takes around 2 minutes')
parser.add_argument('-l', '--lineups', action='store_true', help='output possible lineups to console')
parser.add_argument('-o', '--output', type=str, help='specify output file (default: <day>_<month>.txt)')
args = parser.parse_args()

if args.lineups:
    do_lineups()
    sort('rating')
    print_lineups()
elif args.scrape:
    if args.output:
        output_file = args.output
    print('Scraping...')
    scrape()
    print(f'Scraping Complete!\nOutput file: {output_file}')
