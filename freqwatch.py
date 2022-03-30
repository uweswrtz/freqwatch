#!/usr/bin/env python3
"""
Simple task scheduler to fetch data from freqtrade instances and rendering results in html


TODO:
 -  care about creation of output folders
 
"""

import os
from prefect.schedules import IntervalSchedule
from prefect import Flow, Parameter
from prefect import task
from datetime import datetime, timedelta

# import time
from jinja2 import Environment, FileSystemLoader
import argparse
import inspect
import json
import logging
import re
import sys
from pathlib import Path

import rapidjson

from rest_client import FtRestClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("freqwatch")


def add_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        help="Positional argument defining the command to execute.",
        nargs="?",
    )

    parser.add_argument(
        "--show",
        help="Show possible methods with this client",
        dest="show",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "-c",
        "--config",
        help="Specify configuration file (default: %(default)s). ",
        dest="config",
        type=str,
        metavar="PATH",
        default="config.json",
    )

    parser.add_argument(
        "command_arguments",
        help="Positional arguments for the parameters for [command]",
        nargs="*",
        default=[],
    )

    args = parser.parse_args()
    return vars(args)


def load_file(file):
    fp = Path(file)
    with fp.open("r") as f:
        content = rapidjson.load(
            f, parse_mode=rapidjson.PM_COMMENTS | rapidjson.PM_TRAILING_COMMAS
        )

    return content


@task
def load_config(configfile):

    return load_file(configfile)


def print_commands():
    # Print dynamic help for the different commands using the commands doc-strings
    client = FtRestClient(None)
    print("Possible commands:\n")
    for x, y in inspect.getmembers(client):
        if not x.startswith("_"):
            doc = re.sub(
                ":return:.*", "", getattr(client, x).__doc__, flags=re.MULTILINE
            ).rstrip()
            print(f"{x}\n\t{doc}\n")


def write_raw(botname, botdata, datatype):
    fn = f"{botname}-{datatype}.json"
    filename = os.path.join("html", "raw", fn)

    with open(filename, "w") as f:
        json.dump(botdata, f, indent=4)
        # , sort_keys=True, indent=4)
        # f.write(cp.content)


@task
def get_data(config):

    # logger.info("Starting get_data")
    # if args.get("show"):
    #     print_commands()
    #     sys.exit()

    # storage = {}
    bot_data = []

    for bot in config.get("bots"):
        this_bot_data = {}
        this_bot_data["bot_name"] = str(bot.get("bot_name", {}))

        output = str(bot.get("bot_name", {}))

        # print(output)
        # print('{} {: 4.2f} {}'.format(item['date'], item['abs_profit'], item['trade_count']))
        server_url = bot.get("api_server", {}).get("server_url")
        if server_url == None:
            url = bot.get("api_server", {}).get("listen_ip_address", "127.0.0.1")
            port = bot.get("api_server", {}).get("listen_port", "8080")
            server_url = f"http://{url}:{port}"

        username = bot.get("api_server", {}).get("username")
        password = bot.get("api_server", {}).get("password")
       
        # logger.info('{} {} {}'.format(server_url, username, password))
        this_bot_data["server_url"] = server_url

        client = FtRestClient(server_url, username, password)

        this_bot_data["show_config"] = client.show_config()
        write_raw(
            this_bot_data["bot_name"], this_bot_data["show_config"], "show_config"
        )

        # logger.info(type(this_bot_data['status']))
        # if this_bot_data['show_config'] is not None:

        if this_bot_data["show_config"] and this_bot_data["show_config"].get("detail", "Authorized") != "Unauthorized":
            this_bot_data["last_update_time"] = datetime.utcnow().timestamp() * 1000

            this_bot_data["version"] = client.version()
            write_raw(this_bot_data["bot_name"], this_bot_data["version"], "version")

            this_bot_data["profit"] = client.profit()
            write_raw(this_bot_data["bot_name"], this_bot_data["profit"], "profit")

            this_bot_data["count"] = client.count()

            write_raw(this_bot_data["bot_name"], this_bot_data["count"], "count")

            this_bot_data["status"] = client.status()
            write_raw(this_bot_data["bot_name"], this_bot_data["status"], "status")

            # this_bot_data["strategies"] = client.strategies()
            # write_raw(
            #     this_bot_data["bot_name"], this_bot_data["strategies"], "strategies"
            # )

            this_bot_data["balance"] = client.balance()
            write_raw(
                this_bot_data["bot_name"], this_bot_data["balance"], "balance"
            )

            # this_bot_data["locks"] = client.locks()
            # write_raw(this_bot_data["bot_name"], this_bot_data["locks"], "locks")

            this_bot_data["edge"] = client.edge()
            write_raw(this_bot_data["bot_name"], this_bot_data["edge"], "edge")

            this_bot_data["daily"] = client.daily(days=30)
            write_raw(this_bot_data["bot_name"], this_bot_data["daily"], "daily")

            this_bot_data["daily_data"] = this_bot_data["daily"].get("data")

            output += " {}".format(this_bot_data["show_config"].get("stake_currency"))
            output += " {}".format(this_bot_data["count"].get("current"))
            for item in this_bot_data["daily"].get("data"):

                output += " {:>6.2f} {:>2d}".format(
                    item["abs_profit"], item["trade_count"]
                )
            logger.info(output)
            #bot_data.append(this_bot_data)
        #       except:
        #          logger.error(output + " ERROR")
        # print(this_bot_data)
        elif this_bot_data["show_config"] and this_bot_data["show_config"].get("detail", "Authorized") == "Unauthorized":
            logger.warning("Authorization failed")
            this_bot_data["show_config"] = {"state": "not_authorized"}
            write_raw(
                this_bot_data["bot_name"], this_bot_data["show_config"], "show_config"
            )
        else:
            logger.warning("Connection error - no show_config")
            this_bot_data["show_config"] = {"state": "not_running"}
            write_raw(
                this_bot_data["bot_name"], this_bot_data["show_config"], "show_config"
            )
        
        bot_data.append(this_bot_data)
           

    # logger.info("Stopped get_data")
    # print(bot_data)
    write_raw("bot_data", bot_data, "raw")
    return bot_data


@task
def calculate_per_bot(data):

    now = datetime.utcnow().timestamp()

    #for bot in data:
    for bot in (bot for bot in data if bot["show_config"]["state"] == "running"):
        # logger.info(bot['show_config']['bot_name'])

        if bot["profit"]["first_trade_timestamp"] == 0:
            bot["profit"]["first_trade_days"] = 0
        else:
            bot["profit"]["first_trade_days"] = int(
                divmod(
                    (now - bot["profit"]["first_trade_timestamp"] / 1000), 60 * 60 * 24
                )[0]
            )
        # logger.info(bot['profit']['first_trade_days'])

        if bot["profit"]["first_trade_days"] > 0:
            bot["profit"]["avg_per_day_all_time"] = (
                bot["profit"]["profit_closed_coin"] / bot["profit"]["first_trade_days"]
            )
            bot["profit"]["avg_per_day_all_time_fiat"] = (
                bot["profit"]["profit_closed_fiat"] / bot["profit"]["first_trade_days"]
            )
        else:
            bot["profit"]["avg_per_day_all_time"] = bot["profit"]["profit_closed_coin"]
            bot["profit"]["avg_per_day_all_time_fiat"] = bot["profit"][
                "profit_closed_fiat"
            ]

        if (bot["profit"]["winning_trades"] + bot["profit"]["losing_trades"]) > 0:
            bot["profit"]["winning_rate"] = bot["profit"]["winning_trades"] / (
                bot["profit"]["winning_trades"] + bot["profit"]["losing_trades"]
            )
        else:
            bot["profit"]["winning_rate"] = 0

        bot["profit"]["30d"] = 0
        for daily in bot['daily_data']:
            bot["profit"]["30d"] += daily['fiat_value']

        bot["count"]["nr_long_open"] = 0
        bot["count"]["total_max_needed"] = 0  #
        if bot["count"]["current"] > 0:

            bot["status"][0]["open_days"] = (
                now - bot["status"][0]["open_timestamp"] / 1000
            ) / (60 * 60 * 24)
            bot["status"][0]["open_hours"] = int(
                divmod((now - bot["status"][0]["open_timestamp"] / 1000), 60 * 60)[0]
            )

            for ot in bot["status"]:
                ot["is_long_running"] = False
                if int( divmod((now - ot["open_timestamp"] / 1000), 60 * 60)[0]) > 24:
                    bot["count"]["nr_long_open"] += 1
                    ot["is_long_running"] = True

            # nr more neede to have at least max running
            bot["count"]["total_max_needed"] = bot["count"]["max"] + bot["count"]["nr_long_open"]

        if isinstance(bot["edge"], list):
            bot["show_config"]["edge_pairs_nr"] = len(bot["edge"])
        else:
            bot["show_config"]["edge_pairs_nr"] = 0

    write_raw("all_bots", data, "calculate_per_bot")
    return data
    # sum(item['daily'] for item in myList)


@task
def calculate_totals(data):
    all_bot_data = {}
    all_bot_data["bot_name"] = "all-bots"
    all_bot_data["daily"] = []
    all_bot_data["profit"] = {}
    all_bot_data["profit"]["profit_closed_coin"] = 0
    all_bot_data["profit"]["profit_closed_fiat"] = 0
    all_bot_data["profit"]["winning_trades"] = 0
    all_bot_data["profit"]["losing_trades"] = 0
    all_bot_data["profit"]["today_profit_fiat"] = 0
    all_bot_data["profit"]["yesterday_profit_fiat"] = 0
    all_bot_data["profit"]["30d_profit_fiat"] = 0

    all_bot_data["active_bots"] = len(data)

    # now = datetime.utcnow().timestamp()

    #for bot in data:
    for bot in (bot for bot in data if bot["show_config"]["state"] == "running"):

        all_bot_data["profit"]["profit_closed_coin"] += bot["profit"]["profit_closed_coin"]
        all_bot_data["profit"]["profit_closed_fiat"] += bot["profit"]["profit_closed_fiat"]

        all_bot_data["profit"]["winning_trades"] += bot["profit"]["winning_trades"]
        all_bot_data["profit"]["losing_trades"] += bot["profit"]["losing_trades"]

        # for d in bot['daily']['data']:
        #    all_bot_data[d]

        all_bot_data["daily"] += bot["daily"]["data"]

        all_bot_data["profit"]["today_profit_fiat"] += bot["daily"]["data"][0][
            "fiat_value"
        ]
        all_bot_data["profit"]["yesterday_profit_fiat"] += bot["daily"]["data"][1][
            "fiat_value"
        ]
        all_bot_data["profit"]["30d_profit_fiat"] += bot["profit"]["30d"]

    write_raw("all_bots", all_bot_data, "calculate_totals")

    return all_bot_data

@task
def summary_long_running(data) -> None:

    summary = {}
    for bot in (bot for bot in data if bot["show_config"]["state"] == "running"):
        summary[bot.get("bot_name")] = bot.get("count").get("nr_long_open")

    write_raw("all_bots", summary, "summary_long_running")

@task
def summary_balance(data):

    balance = {}
    for bot in (bot for bot in data if bot["show_config"]["state"] == "running"):
        #logger.info(f'balance for {bot["bot_name"]}')
        bot_exchange = bot["show_config"]["exchange"]
        bot_currency = bot["show_config"]["stake_currency"]
        bot_bal_currencies = bot["balance"]["currencies"]
        if not bot_exchange in balance:
            balance[bot_exchange] = {}
        if bot_currency in balance[bot_exchange]:
            balance[bot_exchange][bot_currency] = min(balance[bot_exchange][bot_currency], next(c for c in bot_bal_currencies if c["currency"] == bot_currency)["free"])
        else:
            cur_in_currencies = [c for c in bot_bal_currencies if c["currency"] == bot_currency]
            if len(cur_in_currencies) >0:
                #logger.info(f'balance cur_in_currencies {cur_in_currencies}')
                balance[bot_exchange][bot_currency] = cur_in_currencies[0]["free"]

    write_raw("all_bots", balance, "balance")
    return balance

@task
def write_html(data, totals, folder, template_name = "index.html") -> None:
    # logger.info("write_html")
    # print("Hello, {}!".format(person))

    file_loader = FileSystemLoader("templates")
    env = Environment(loader=file_loader)

    template = env.get_template(template_name)

    output = template.render(
        bot_data=data, now=datetime.today().strftime("%Y-%m-%d-%H:%M:%S"), totals=totals
    )

    with open(f"{folder}/{template_name}", "w") as fh:
        fh.write(output)



# schedule to run every 12 hours
schedule = IntervalSchedule(
    start_date=datetime.utcnow() + timedelta(seconds=1), interval=timedelta(minutes=5)
)


# define Prefect flow
with Flow("FREQWATCH", schedule=schedule) as flow:
    configfile = Parameter("configfile", default="config.json")
    output = Parameter("output", default="html")
    config = load_config(configfile)
    # config = load_config('config-default.json')
    data = get_data(config)
    # houston_realtor_data = transform(realtor_data)
    # load_to_database = load(houston_realtor_data)
    data = calculate_per_bot(data)
    summary_long_running(data)
    balance = summary_balance(data)
    totals = calculate_totals(data)
    write_html(data, totals, output)

if __name__ == "__main__":
    arguments = add_arguments()

    if arguments.get("show"):
        print_commands()
        sys.exit()

    command = arguments["command"]
    command_args = arguments.get('command_arguments')
    logger.info(f"Arguments: {command_args} ({len(command_args)})")


    flow.run(configfile=arguments["config"])
