from datetime import date, datetime, timedelta
from enum import IntEnum
from selenium import webdriver
from time import sleep

import argparse
import re
import sys

from selenium.webdriver.chrome.service import Service


class WeekDay(IntEnum):
    Mon = 0
    Tue = 1
    Wed = 2
    Thu = 3
    Fri = 4
    Sat = 5
    Sun = 6


def get_desired_week_days(week_days_str):
    if not week_days_str:
        return None
    return [WeekDay[week_day] for week_day in week_days_str.split(",")]


def date_range(start_date, end_date, week_days):
    for n in range(int((end_date - start_date).days)):
        curr_date = start_date + timedelta(n)
        if week_days:
            curr_week_day = curr_date.weekday()
            if curr_week_day not in week_days:
                continue
        yield curr_date


def extract_airlines_from_flight_text(flight_text):
    """

    :param flight_text: Raw flight text string, e.g.,
        "3:45 PM – 8:15 PM+1\nItaly\n13h 30m\nSFO–PVG\nNonstop\n$4,823",
        "12:51 PM – 4:50 PM+1\nAustria\n12h 59m\nSEA–PVG\nNonstop\n$4,197",
        "2:10 AM – 1:25 PM+1\nSeparate tickets booked together\nEVA Air, Spring\n20h 15m\nSEA–PVG\n1 stop\n6h 15m TPE\n$1,194"
    :return: A list of airlines, e.g., ["Italy"], ["Delta", "Austria"], ["Al Italia ", "Spring"]
    """
    airlines = []
    for airline_candidate in flight_text.split("\n")[1:]:
        if airline_candidate == "Separate tickets booked together":
            continue
        if re.match(r"(\d+h )?\d+m", airline_candidate):
            break
        airlines.extend(airline_candidate.split(","))
    return airlines


def extract_flight_number_from_flight_container(flight):
    flight_summary = flight.find_elements_by_class_name("gws-flights-results__result-item-summary")
    flight_number_str = flight_summary[0].find_elements_by_tag_name("span")[0].get_attribute("id")
    return flight_number_str[13:]


def filter_flight(flight, desired_airlines, desired_flight_number):
    if not desired_airlines and not desired_flight_number:
        return True
    if desired_airlines:
        airlines = extract_airlines_from_flight_text(flight.text)
        if not (set(desired_airlines) & set(airlines)):
            return False
    if desired_flight_number:
        flight_number = extract_flight_number_from_flight_container(flight)
        if desired_flight_number != flight_number:
            return False
    return True


def print_flight_info(flight_list, curr_date):
    print("Found {} flights on {} ({})".format(
        len(flight_list), curr_date.strftime("%Y-%m-%d"), WeekDay(curr_date.weekday()).name))
    print("*******************************************")
    for flight in flight_list:
        print(repr(flight))


def keep_playing_success():
    while True:
        sleep(timedelta(minutes=1).total_seconds())


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Search for the flights on the earliest date given a date range",
    )
    parser.add_argument(
        "-c",
        "--chromedriver-path",
        required=True,
        help="Full path to the ChromeDriver executable"
    )
    parser.add_argument(
        "-u",
        "--Ryanair-flights-url",
        required=True,
        help="""Ryanair flights url where the exact date is replaced with a formatting 
        https://www.ryanair.com/gb/en?hl=en#flt=SEA./m/06wjf.{date};c:USD;e:1;s:1;sd:1;st:none;t:f;tt:o
        """
    )
    parser.add_argument(
        "-a",
        "--airlines",
        help="Desired airlines separated by commas, e.g., 'Italy,Austria,Albania'"
    )
    parser.add_argument(
        "-f",
        "--flight_number",
        help="Desired flight number, e.g., UA857, DL287"
    )
    parser.add_argument(
        "-s",
        "--start-date",
        default=date.today().strftime("%Y-%m-%d"),
        help="Start date in the format of YYYY-MM-DD"
    )
    parser.add_argument(
        "-e",
        "--end-date",
        required=True,
        help="End date in the format of YYYY-MM-DD"
    )
    parser.add_argument(
        "-w",
        "--week-days",
        help="""Weekdays of the desired dates separated by commas,
        e.g., "Wed,Sat"
        """
    )
    parser.add_argument(
        "-r",
        "--retry-interval",
        type=int,
        default=30,
        help="Retry interval in minutes"
    )
    args = parser.parse_args()

    s = Service('C:/Users/User/Downloads/chromedriver.exe')
    driver = webdriver.Chrome(service=s)
    sleep(timedelta(seconds=5).total_seconds())

    airlines = args.airlines.split(",") if args.airlines else None
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    week_days = get_desired_week_days(args.week_days)
    found_flights = False
    while True:
        try:
            for curr_date in date_range(start_date, end_date, week_days):
                ryanair_flights_url = args.google_flights_url.format(date=curr_date.strftime("%Y-%m-%d"))
                print("Opening {}".format(ryanair_flights_url))
                driver.get(ryanair_flights_url)
                sleep(timedelta(seconds=3).total_seconds())
                xp_results_table = "//li[contains(@class, 'gws-flights-results__result-item')]"
                flight_containers = driver.find_element(
                    xp_results_table)
                flight_list = [flight.text for flight in flight_containers
                               if filter_flight(flight, airlines, args.flight_number)]
                if flight_list:
                    print_flight_info(flight_list, curr_date)
                    found_flights = True
                    break
            if found_flights:
                keep_playing_success()
            else:
                print("No flights found. Sleeping {} minutes before retrying".format(args.retry_interval))
                sleep(timedelta(minutes=args.retry_interval).total_seconds())
        except KeyboardInterrupt:
            print("Program exiting...")
            sys.exit()


if __name__ == "__main__":
    main()
