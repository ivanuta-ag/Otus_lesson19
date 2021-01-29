import argparse
import re
import json
from collections import defaultdict, Counter
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description='Log file parser')
parser.add_argument('-f', dest='file', action='store', help='Path to logfile or log files')
args = parser.parse_args()

line_format = re.compile(
    r"(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|.*) - - "
    r"\[(?P<dateandtime>\d{2}\/[A-Za-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} "
    r'(\+|\-)\d{4})\] ((\"(POST|GET|PUT|DELETE|HEAD) )(?P<url>.+)(HTTP\/1\.1")) '
    r'(?P<statuscode>\d{3}) (?P<bytessent>\d+) (["](?P<refferer>(\-)|(.+))["]) (["](?P<useragent>.+)["]) '
    r"(?P<time>\d+$)"
)

try:
    with open(args.file) as file:

        dict_requests = defaultdict(int)
        dict_methods = defaultdict(
            lambda: {"GET": 0, "POST": 0, "PUT": 0, "DELETE": 0, "HEAD": 0}
        )
        dict_count_ip = {"top_ip": defaultdict(int)}
        dict_client_error = defaultdict(
            lambda: {"method": None, "url": None, "status": None, "ip": None, "count": 0}
        )
        dict_server_error = defaultdict(
            lambda: {"method": None, "url": None, "status": None, "ip": None, "count": 0}
        )
        dict_long_requests = defaultdict(
            lambda: {"method": None, "url": None, "ip": None, "time": 0}
        )

        for index, line in enumerate(file.readlines()):
            data = re.search(line_format, line)

            if data:
                datadict = data.groupdict()
                ip = datadict["ipaddress"]
                method = data.group(6)
                url = datadict["url"]
                status = datadict["statuscode"]

                datetimestring = datadict["dateandtime"]
                bytessent = datadict["bytessent"]
                referrer = datadict["refferer"]
                useragent = datadict["useragent"]

                requesttime = datadict["time"]

                dict_requests["count_requests"] += 1
                dict_requests = dict(dict_requests)
                dict_methods["count_method"][method] += 1
                dict_methods = dict(dict_methods)
                dict_count_ip["top_ip"][ip] += 1

                dict_long_requests[index]["method"] = method
                dict_long_requests[index]["url"] = url
                dict_long_requests[index]["ip"] = ip
                dict_long_requests[index]["time"] = requesttime


                def error_request(dict_error: dict):
                    dict_error[url]["method"] = method
                    dict_error[url]["url"] = url
                    dict_error[url]["status"] = status
                    dict_error[url]["ip"] = ip
                    dict_error[url]["count"] += 1


                if 400 <= int(status) < 500:
                    error_request(dict_client_error)

                if 500 <= int(status) < 600:
                    error_request(dict_server_error)

        top_ip = Counter(dict_count_ip["top_ip"])
        top_ip = top_ip.most_common(10)
        dict_count_ip["top_ip"] = list(dict(top_ip).keys())


        def top_ten_request(dict_request: dict, count: str) -> dict:
            dict_url = {}
            for i in dict_request:
                dict_url[i] = dict_request[i][count]
            count_request = Counter(dict_url)
            count_request = count_request.most_common(10)
            top_request = {}
            for i in count_request:
                key = i[0]
                top_request[key] = dict_request[key]
            return top_request


        top_client_error = top_ten_request(dict_client_error, "count")
        top_server_error = top_ten_request(dict_server_error, "count")
        top_long_requests = top_ten_request(dict_long_requests, "time")

        statistic = {
            "count_request": dict_requests,
            "total_number_of_completed_requests": dict_methods,
            "top_10_ip": dict_count_ip,
            "top_10_long_requests": top_long_requests,
            "top_10_client_error": top_client_error,
            "top_10_server_error": top_server_error,
        }

        with open("log_results.json", "w") as outfile:
            json.dump(statistic, outfile, indent=4)

except Exception:
    e = sys.exc_info()[1]
    print(e.args[0])
