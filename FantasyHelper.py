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
Player('karrigan', 181, 'FaZe', 0.98), Player('rain', 209, 'FaZe', 1.14), Player('Twistzz', 213, 'FaZe', 1.11), Player('ropz', 221, 'FaZe', 1.17), Player('broky', 223, 'FaZe', 1.17), 
Player('s1mple', 0, 'Natus Vincere', 1.34), Player('electroNic', 0, 'Natus Vincere', 1.10), Player('Boombl4', 0, 'Natus Vincere', 0.98), Player('Perfecto', 0, 'Natus Vincere', 1.06), Player('b1t', 0, 'Natus Vincere', 1.17), 
Player('Snappi', 187, 'ENCE', 1.00), Player('Maden', 194, 'ENCE', 1.03), Player('dycha', 211, 'ENCE', 1.12), Player('hades', 207, 'ENCE', 1.09), Player('Snax', 209, 'ENCE', 0.89), 
Player('cadiaN', 198, 'Heroic', 1.09), Player('refrezh', 188, 'Heroic', 1.01), Player('stavn', 227, 'Heroic', 1.20), Player('TeSeS', 201, 'Heroic', 1.11), Player('sjuush', 197, 'Heroic', 1.06), 
Player('es3tag', 182, 'NIP', 0.98), Player('REZ', 211, 'NIP', 1.20), Player('hampus', 194, 'NIP', 1.02), Player('Brollan', 208, 'NIP', 1.14), Player('Plopski', 190, 'NIP', 1.03), 
Player('chopper', 0, 'Spirit', 0.99), Player('degster', 0, 'Spirit', 1.28), Player('magixx', 0, 'Spirit', 1.13), Player('s1ren', 0, 'Spirit', 1.08), Player('Patsi', 0, 'Spirit', 1.11), 
Player('JACKZ', 183, 'G2', 0.93), Player('NiKo', 235, 'G2', 1.13), Player('huNter-', 214, 'G2', 1.16), Player('Aleksib', 174, 'G2', 0.89), Player('m0NESY', 216, 'G2', 1.14), 
Player('arT', 195, 'FURIA', 1.06), Player('yuurih', 215, 'FURIA', 1.22), Player('KSCERATO', 217, 'FURIA', 1.16), Player('saffee', 215, 'FURIA', 1.04), Player('drop', 186, 'FURIA', 1.03), 
Player('HObbit', 214, 'Cloud9', 1.14), Player('interz', 186, 'Cloud9', 0.96), Player('Ax1Le', 223, 'Cloud9', 1.20), Player('sh1ro', 234, 'Cloud9', 1.25), Player('nafany', 183, 'Cloud9', 0.91), 
Player('apEX', 188, 'Vitality', 0.95), Player('dupreeh', 200, 'Vitality', 1.02), Player('Magisk', 200, 'Vitality', 1.08), Player('ZywOo', 236, 'Vitality', 1.20), Player('misutaaa', 181, 'Vitality', 0.92), 
Player('HooXi', 0, 'Copenhagen Flames', 0.88), Player('nicoodoz', 0, 'Copenhagen Flames', 1.12), Player('roeJ', 0, 'Copenhagen Flames', 1.21), Player('jabbi', 0, 'Copenhagen Flames', 1.11), Player('Zyphon', 0, 'Copenhagen Flames', 1.05), 
Player('Xyp9x', 174, 'Astralis', 0.93), Player('gla1ve', 178, 'Astralis', 0.96), Player('k0nfig', 204, 'Astralis', 1.13), Player('Farlig', 192, 'Astralis', 1.02), Player('blameF', 224, 'Astralis', 1.25), 
Player('shox', 181, 'Liquid', 0.98), Player('nitr0', 180, 'Liquid', 1.00), Player('NAF', 217, 'Liquid', 1.21), Player('EliGE', 211, 'Liquid', 1.20), Player('oSee', 216, 'Liquid', 1.15), 
Player('FL1T', 0, 'Outsiders', 1.05), Player('Qikert', 0, 'Outsiders', 1.02), Player('Jame', 0, 'Outsiders', 1.09), 
Player('fnx', 174, 'Imperial', 0.94), Player('FalleN', 196, 'Imperial', 1.11), Player('fer', 228, 'Imperial', 1.23), Player('boltz', 211, 'Imperial', 1.13), Player('VINI', 204, 'Imperial', 1.10), 
Player('tabseN', 205, 'BIG', 1.12), Player('tiziaN', 177, 'BIG', 0.98), Player('syrsoN', 215, 'BIG', 1.17), Player('faveN', 213, 'BIG', 1.10), Player('Krimbo', 205, 'BIG', 1.05), 
Player('NickelBack', 0, 'Entropiq', 1.04), Player('Krad', 0, 'Entropiq', 1.09), Player('Lack1', 0, 'Entropiq', 0.92), Player('El1an', 0, 'Entropiq', 1.11), Player('Forester', 0, 'Entropiq', 1.13), 
Player('alex', 195, 'Movistar Riders', 1.08), Player('mopoz', 183, 'Movistar Riders', 0.99), Player('DeathZz', 182, 'Movistar Riders', 0.99), Player('SunPayus', 208, 'Movistar Riders', 1.17), Player('dav1g', 172, 'Movistar Riders', 0.93), 
Player('rigoN', 0, 'Bad News Eagles', 1.11), Player('SENER1', 0, 'Bad News Eagles', 0.96), Player('juanflatroo', 0, 'Bad News Eagles', 1.08), Player('sinnopsyy', 0, 'Bad News Eagles', 1.04), Player('gxx-', 0, 'Bad News Eagles', 1.05), 
Player('dexter', 174, 'MOUZ', 0.96), Player('frozen', 211, 'MOUZ', 1.17), Player('JDC', 195, 'MOUZ', 1.05), Player('torzsi', 214, 'MOUZ', 1.13), Player('Bymas', 203, 'MOUZ', 1.13), 
Player('Jerry', 0, 'forZe', 1.06), Player('zorte', 0, 'forZe', 1.10), Player('shalfey', 0, 'forZe', 1.14), Player('KENSI', 0, 'forZe', 1.13), Player('Norwi', 0, 'forZe', 1.05), 
Player('chelo', 0, 'MIBR', 1.19), Player('exit', 0, 'MIBR', 1.10), Player('Tuurtle', 0, 'MIBR', 1.10), Player('JOTA', 0, 'MIBR', 1.26), Player('brnz4n', 0, 'MIBR', 1.23), 
Player('bodyy', 0, 'HEET', 1.10), Player('Lucky', 0, 'HEET', 1.03), Player('Djoko', 0, 'HEET', 1.06), Player('Ex3rcice', 0, 'HEET', 1.01), Player('afro', 0, 'HEET', 1.06), 
Player('JT', 179, 'Complexity', 0.96), Player('floppy', 213, 'Complexity', 1.16), Player('Grim', 185, 'Complexity', 1.10), Player('junior', 207, 'Complexity', 1.03), Player('FaNg', 197, 'Complexity', 0.99), 
Player('XANTARES', 0, 'Eternal Fire', 1.27), Player('woxic', 0, 'Eternal Fire', 1.12), Player('Calyx', 0, 'Eternal Fire', 1.07), Player('imoRR', 0, 'Eternal Fire', 1.11), Player('xfl0ud', 0, 'Eternal Fire', 1.04), 
Player('PKL', 0, 'paiN', 1.05), Player('NEKIZ', 0, 'paiN', 1.11), Player('hardzao', 0, 'paiN', 1.11), Player('biguzera', 0, 'paiN', 1.16), Player('nython', 0, 'paiN', 1.17), 
Player('nexa', 0, 'OG', 0.96), Player('niko', 0, 'OG', 0.87), Player('mantuu', 0, 'OG', 1.26), Player('flameZ', 0, 'OG', 0.95), 
Player('max', 0, '9z', 1.08), Player('dgt', 0, '9z', 1.22), Player('Luken', 0, '9z', 1.10), Player('rox', 0, '9z', 0.86), Player('dav1d', 0, '9z', 0.99), 
Player('HEN1', 0, 'GODSENT', 1.10), Player('TACO', 0, 'GODSENT', 0.92), Player('dumau', 0, 'GODSENT', 1.21), Player('b4rtiN', 0, 'GODSENT', 1.05), Player('latto', 0, 'GODSENT', 1.07), 
Player('bubble', 0, 'SKADE', 0.94), Player('dream3r', 0, 'SKADE', 1.09), Player('SHiPZ', 0, 'SKADE', 1.12), Player('dennyslaw', 0, 'SKADE', 1.10), Player('Rainwaker', 0, 'SKADE', 1.12), 
]

# has to be global for -o option to work
# gets latest monday (update day for hltv rankings)
date = datetime.today()
year = date.year
month = date.strftime('%B')
today = date.today()
day = today - timedelta(days=today.weekday())
day = day.strftime('%d')
output_file = f'{day}_{month.lower()}.txt'

teams = ['FaZe', 'FURIA', 'ENCE']  # teams you want players from
p_whitelist = []  # players that must be in lineup
p_blacklist = []  # players that can't be in lineup
min_value = 999  # discard lineups under this value

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
do_lineups()
sort('rating')
print_lineups()
