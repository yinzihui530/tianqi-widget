import sys, requests, re, subprocess, webbrowser, json, os, shutil, time, threading
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QMenu, QAction
from PyQt5.QtCore import QTimer, Qt, QEvent
from PyQt5.QtGui import QFont, QFontMetrics

CITIES = {
    "邯郸": "AwDQd", "邢台": "WgyJx", "石家庄": "uJQqI", "保定": "FaykR",
    "沧州": "mHkdW", "衡水": "Jiheq", "雄安新区": "FTACx",
}

IMG_ICON_MAP = {
    "0": "☀️", "1": "⛅", "2": "☁️", "3": "🌧️", "4": "⛈️", "5": "🌨️",
    "6": "🌧️", "7": "🌧️", "8": "🌧️", "9": "🌧️", "10": "⛈️", "11": "⛈️",
    "12": "⛈️", "13": "❄️", "14": "🌨️", "15": "🌨️", "16": "❄️", "17": "❄️",
    "18": "🌫️", "19": "🌫️", "20": "🌪️", "29": "🌪️", "30": "🌫️", "31": "🌪️", "53": "🌫️",
}

def clean_text(val, default="—"):
    s = str(val)
    if not s or s in ["9999", "999", "999999", "None", ""]:
        return default
    return s

def get_weather_str(weather_obj):
    info = clean_text(weather_obj.get("info"))
    img = clean_text(weather_obj.get("img"), default="")
    icon = IMG_ICON_MAP.get(img, "❔") if info != "—" else "❔"
    return info, icon

def get_temp_str(weather_obj):
    return clean_text(weather_obj.get("temperature"))

def highlight(val_str, threshold, is_gt=True, unit=""):
    if val_str == "—" or val_str == "0.0" or val_str == "0":
        return f"{val_str}{unit}"
    try:
        num_match = re.search(r'\d+(\.\d+)?', str(val_str))
        if not num_match:
            return f"{val_str}{unit}"
        num = float(num_match.group())
        
        if is_gt and num > threshold:
            return f"<span style='color:#FF4B4B;'>{val_str}{unit}</span>"
        if not is_gt and num < threshold:
            return f"<span style='color:#FF4B4B;'>{val_str}{unit}</span>"
    except Exception:
        pass
    return f"{val_str}{unit}"

def open_in_browser(url):
    if shutil.which("qaxbrowser-safe"):
        subprocess.Popen(["qaxbrowser-safe", f"--app={url}"])
    elif shutil.which("qaxbrowser"):
        subprocess.Popen(["qaxbrowser", f"--app={url}"])
    elif shutil.which("google-chrome"):
        subprocess.Popen(["google-chrome", f"--app={url}"])
    elif shutil.which("chromium"):
        subprocess.Popen(["chromium", f"--app={url}"])
    else:
        webbrowser.open(url)
        return

    threading.Thread(target=force_fullscreen_later, daemon=True).start()

def force_fullscreen_later():
    time.sleep(0.5) 
    try:
        out = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if "nmc.cn" in line or "中央气象台" in line or "天气" in line or ".html" in line:
                win_id = line.split()[0]
                subprocess.run(["wmctrl", "-i", "-a", win_id], check=False)
                subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", "add,fullscreen"], check=False)
    except Exception as e:
        pass

def open_raw_data(city_name, station_code):
    url = f"https://www.nmc.cn/rest/weather?stationid={station_code}"
    try:
        r = requests.get(url, timeout=15).json()
        data = r.get("data", {})
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{city_name} - 原始数据</title>
            <style>
                body {{ background-color: #282c34; color: #abb2bf; font-family: monospace; padding: 20px; }}
                pre {{ background-color: #21252b; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                h2 {{ color: #61afef; }}
            </style>
        </head>
        <body>
            <h2>{city_name} (站点: {station_code}) 中央气象台原始数据</h2>
            <p>获取时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>
        </body>
        </html>
        """
        file_path = f"/tmp/nmc_raw_{station_code}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        open_in_browser(f"file://{file_path}")
    except Exception as e:
        print(f"获取 {city_name} 原始数据失败: {e}")

def open_week_data(city_name, station_code):
    url = f"https://www.nmc.cn/rest/weather?stationid={station_code}"
    try:
        r = requests.get(url, timeout=15).json()
        data = r.get("data", {})
        detail = data.get("predict", {}).get("detail", [])

        days_data = []
        for i, day in enumerate(detail):
            date_str = day.get("date", "")
            date_label = "今天" if i == 0 else ("明天" if i == 1 else date_str[5:])
            
            d_weather = day.get("day", {}).get("weather", {})
            n_weather = day.get("night", {}).get("weather", {})
            
            # 获取最原始的字符串，不做任何默认值替换
            raw_d_img = str(d_weather.get("img", ""))
            raw_d_temp = str(d_weather.get("temperature", ""))
            raw_n_temp = str(n_weather.get("temperature", ""))
            
            # 🌟 核心修复逻辑：
            # 判断是否为真实数据的唯一标准：天气图标代码是不是 9999
            if raw_d_img in ["9999", "999", "None", ""] or raw_d_temp in ["9999", "999", "None", ""]:
                d_temp_val = None  # 确实是无效数据，跳过画点
            else:
                try:
                    d_temp_val = float(raw_d_temp)
                except:
                    d_temp_val = None
            
            try:
                n_temp_val = float(raw_n_temp) if raw_n_temp not in ["9999", "999", "None", ""] else None
            except:
                n_temp_val = None

            days_data.append({
                "date": date_label,
                "d_info": clean_text(d_weather.get("info"), "--"),
                "n_info": clean_text(n_weather.get("info"), "--"),
                "d_temp": d_temp_val,
                "n_temp": n_temp_val,
                "d_icon": IMG_ICON_MAP.get(clean_text(d_weather.get("img"), ""), ""),
                "n_icon": IMG_ICON_MAP.get(clean_text(n_weather.get("img"), ""), ""),
                "precip": clean_text(day.get("precipitation"), "0.0")
            })

        # --- 数学计算（安全过滤掉 None） ---
        valid_temps = [d["d_temp"] for d in days_data if d["d_temp"] is not None] + \
                      [d["n_temp"] for d in days_data if d["n_temp"] is not None]
        
        # 如果全都是 None，给个默认区间
        if not valid_temps:
            max_t, min_t = 10, 0
        else:
            max_t = max(valid_temps + [10])
            min_t = min(valid_temps + [0])
        
        try:
            precip_vals = [float(d["precip"]) for d in days_data]
        except:
            precip_vals = [0] * len(days_data)
        max_p = max(precip_vals + [1])

        # SVG 高度拉长到 300
        svg_h = 300
        t_top, t_bottom = 30, 190
        t_usable = t_bottom - t_top
        p_top, p_bottom = 210, 270
        p_usable = p_bottom - p_top

        # 生成路径
        def gen_temp_path(key):
            pts = []
            for i, d in enumerate(days_data):
                val = d[key]
                if val is None: continue
                x = i * 100 + 50
                y = t_bottom - ((val - min_t) / (max_t - min_t) * t_usable if max_t != min_t else t_usable/2)
                pts.append(f"{x},{y}")
            return "M " + " L ".join(pts) if pts else ""

        def gen_precip_path():
            pts = []
            for i, d in enumerate(days_data):
                x = i * 100 + 50
                val = float(d["precip"])
                y = p_bottom - (val / max_p * p_usable)
                pts.append(f"{x},{y}")
            return "M " + " L ".join(pts)

        path_high = gen_temp_path("d_temp")
        path_low = gen_temp_path("n_temp")
        path_precip = gen_precip_path()

        # 生成数据点和文字
        def gen_temp_points(key, color, is_top=True):
            html_str = ""
            for i, d in enumerate(days_data):
                val = d[key]
                if val is None: continue
                x = i * 100 + 50
                y = t_bottom - ((val - min_t) / (max_t - min_t) * t_usable if max_t != min_t else t_usable/2)
                label = f"{val:.0f}°"
                html_str += f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" />'
                ty = y - 10 if is_top else y + 16
                html_str += f'<text x="{x}" y="{ty}" fill="{color}" font-size="13" font-weight="bold" text-anchor="middle">{label}</text>'
            return html_str

        def gen_precip_points():
            html_str = ""
            for i, d in enumerate(days_data):
                x = i * 100 + 50
                val = float(d["precip"])
                y = p_bottom - (val / max_p * p_usable)
                label = f"{val}mm"
                html_str += f'<circle cx="{x}" cy="{y}" r="3" fill="#98c379" />'
                html_str += f'<text x="{x}" y="{y - 8}" fill="#98c379" font-size="12" font-weight="bold" text-anchor="middle">{label}</text>'
            return html_str

        points_high = gen_temp_points("d_temp", "#e5c07b", True)
        points_low = gen_temp_points("n_temp", "#56b6c2", False)
        points_precip = gen_precip_points()

        # 表格渲染部分
        def render_td(val, default="--"):
            return str(val) if val is not None else default

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{city_name} - 未来一周预报</title>
            <style>
                body {{ background-color: #1e2227; color: #abb2bf; font-family: "Microsoft YaHei", sans-serif; padding: 20px; }}
                h2 {{ color: #61afef; text-align: center; margin-bottom: 30px; }}
                .table-container {{ width: 100%; max-width: 1000px; margin: 0 auto; background-color: #21252b; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
                table {{ width: 100%; border-collapse: collapse; text-align: center; table-layout: fixed; }}
                th, td {{ padding: 10px 5px; border-bottom: 1px solid #323842; }}
                th {{ background-color: #2c313a; color: #e5c07b; font-weight: bold; font-size: 15px; }}
                td {{ font-size: 14px; }}
                .day-style {{ color: #e5c07b; font-weight: bold; font-size: 15px; }}
                .night-style {{ color: #56b6c2; font-size: 14px; }}
                .precip-style {{ color: #98c379; font-weight: bold; }}
                .chart-svg {{ width: 100%; height: 300px; display: block; margin: 0 auto; }}
            </style>
        </head>
        <body>
            <h2>{city_name} - 未来七天预报走势</h2>
            <div class="table-container">
                <table>
                    <tr>
                        <th style="width: 12%;">日期</th>
                        {"".join(f"<th>{d['date']}</th>" for d in days_data)}
                    </tr>
                    <tr>
                        <td style="background-color: #2c313a; color:#e5c07b; font-weight:bold;">白天</td>
                        {"".join(f"<td class='day-style'>{d['d_icon']} {render_td(d['d_info'])}</td>" for d in days_data)}
                    </tr>
                    <tr>
                        <td style="background-color: #2c313a; color:#56b6c2; font-weight:bold;">夜间</td>
                        {"".join(f"<td class='night-style'>{d['n_icon']} {render_td(d['n_info'])}</td>" for d in days_data)}
                    </tr>
                    <tr>
                        <td style="background-color: #2c313a; color:#98c379; font-weight:bold;">降水</td>
                        {"".join(f"<td class='precip-style'>{d['precip']}mm</td>" for d in days_data)}
                    </tr>
                    <!-- 双轨折线图行 -->
                    <tr>
                        <td style="background-color: #2c313a; color:#e5c07b; font-weight:bold; font-size:12px;">趋势图</td>
                        <td colspan="7" style="padding: 0; position: relative;">
                            <svg viewBox="0 0 700 300" preserveAspectRatio="none" class="chart-svg">
                                <line x1="0" y1="30" x2="700" y2="30" stroke="#3e4451" stroke-width="1" stroke-dasharray="3,3"/>
                                <line x1="0" y1="110" x2="700" y2="110" stroke="#3e4451" stroke-width="1" stroke-dasharray="3,3"/>
                                <line x1="0" y1="190" x2="700" y2="190" stroke="#3e4451" stroke-width="1" stroke-dasharray="3,3"/>
                                
                                <path d="{path_high}" fill="none" stroke="#e5c07b" stroke-width="3" stroke-linejoin="round" />
                                {points_high}
                                
                                <path d="{path_low}" fill="none" stroke="#56b6c2" stroke-width="3" stroke-linejoin="round" />
                                {points_low}

                                <line x1="0" y1="200" x2="700" y2="200" stroke="#5c6370" stroke-width="2" />
                                
                                <line x1="0" y1="210" x2="700" y2="210" stroke="#3e4451" stroke-width="1" stroke-dasharray="3,3"/>
                                <line x1="0" y1="270" x2="700" y2="270" stroke="#3e4451" stroke-width="1" stroke-dasharray="3,3"/>

                                <path d="{path_precip}" fill="none" stroke="#98c379" stroke-width="2.5" stroke-dasharray="5,5" stroke-linejoin="round" />
                                {points_precip}
                            </svg>
                        </td>
                    </tr>
                </table>
            </div>
            <div style="text-align: center; margin-top: 15px; color: #5c6370; font-size: 12px;">
                上半区：温度走势 (黄线最高温，蓝线最低温) | 下半区：降水走势 (绿虚线)
            </div>
        </body>
        </html>
        """
        
        file_path = f"/tmp/nmc_week_{station_code}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)
            
        open_in_browser(f"file://{file_path}")
    except Exception as e:
        print(f"获取 {city_name} 一周预报失败: {e}")


class RainWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnBottomHint |
            Qt.Window
        )
        self.setAttribute(Qt.WA_X11NetWmWindowTypeDock)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.label = QLabel("加载中...", self)
        self.font_size = 19
        self.label.setStyleSheet(
            f"color: white; font-size: {self.font_size}px; "
            "background-color: rgba(0, 0, 0, 180); "
            "border: 2px solid rgba(255, 255, 255, 180); "
            "border-radius: 6px; padding: 10px;"
        )
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.label.setWordWrap(True)
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        self.window_width = 850
        self.resize(self.window_width, 780)
        self._positioned = False
        
        self.last_success_time = None
        self.last_html_content = ""
        self.radar_links = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_and_refresh)
        self.timer.start(1 * 60 * 1000) 
        self.fetch()

    def check_and_refresh(self):
        now = datetime.now()
        if self.last_success_time is None or (now - self.last_success_time) > timedelta(minutes=30):
            self.fetch()

    def reposition(self):
        screen = QApplication.primaryScreen().availableGeometry()
        margin = 20
        x = screen.right() - self.width() - margin
        y = screen.top() + margin
        self.move(x, y)

    def showEvent(self, e):
        if not self._positioned:
            self.reposition()
            self._positioned = True
            QTimer.singleShot(1000, self.force_below_with_wmctrl)
        super().showEvent(e)

    def force_below_with_wmctrl(self):
        try:
            self.setWindowTitle("WeatherWidgetBottom")
            subprocess.run(["wmctrl", "-r", "WeatherWidgetBottom", "-b", "add,below,sticky"], check=False)
        except Exception as e:
            pass

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                self.showNormal()
                QTimer.singleShot(200, self.force_below_with_wmctrl)
        super().changeEvent(event)

    def fetch(self):
        prov_warning_html = ""
        city_lines = []
        
        valid_radar_cities = ["邯郸", "石家庄", "沧州"]
        self.radar_links = {}
        
        allowed_cities = ["邯郸", "邢台", "石家庄", "保定", "沧州", "衡水", "雄安新区"]
        all_hebei_cities = ["张家口", "承德", "唐山", "秦皇岛", "廊坊", "定州", "辛集"]

        success_count = 0

        try:
            for name, code in CITIES.items():
                url = f"https://www.nmc.cn/rest/weather?stationid={code}"
                r = requests.get(url, timeout=15).json()
                data = r.get("data", {})
                real = data.get("real", {})
                predict = data.get("predict", {})
                detail = predict.get("detail", [])
                
                if name in valid_radar_cities:
                    radar_data = data.get("radar", {})
                    if radar_data and radar_data.get("url"):
                        self.radar_links[name] = "https://www.nmc.cn" + radar_data.get("url")

                if not real:
                    raise ValueError(f"{name} 数据缺失")

                warn_data = real.get("warn", {})
                warn_city = clean_text(warn_data.get("city"))
                warn_content = clean_text(warn_data.get("issuecontent"))
                warn_alert = clean_text(warn_data.get("alert"))

                if not prov_warning_html and warn_city == "—" and "省气象台" in warn_alert:
                    if any(city in warn_content for city in allowed_cities):
                        body_text = warn_content.split("：", 1)[1] if "：" in warn_content else warn_content
                        for c in all_hebei_cities:
                            body_text = re.sub(rf'[、和]?{c}[、和]?', '', body_text)
                        body_text = re.sub(r'、+', '、', body_text)
                        body_text = re.sub(r'^[、和\s]+', '', body_text)
                        body_text = re.sub(r'。?请注意防范[。！!]?$', '', body_text)
                        
                        prov_warning_html = (
                            f"<span style='color:#FFD700;'><b>⚠️ {warn_alert}</b></span><br>"
                            f"<span style='color:#E0E0E0;'>{body_text}</span>"
                        )

                cur_weather_obj = real.get("weather", {})
                cur_text, cur_icon = get_weather_str(cur_weather_obj)
                
                raw_temp = get_temp_str(cur_weather_obj)
                if raw_temp != "—":
                    try:
                        t = float(raw_temp)
                        if t > 40 or t < -10:
                            cur_temp = f"<span style='color:#FF4B4B;'>{raw_temp}</span>"
                        else:
                            cur_temp = raw_temp
                    except:
                        cur_temp = raw_temp
                else:
                    cur_temp = raw_temp

                raw_hum = clean_text(cur_weather_obj.get("humidity"))
                cur_hum = highlight(raw_hum, 90, is_gt=True, unit="") 

                raw_rain = clean_text(cur_weather_obj.get("rain"), default="0.0")
                cur_rain = highlight(raw_rain, 50, is_gt=True, unit="mm")
                
                cur_wind = real.get("wind", {})
                cur_wind_dir = clean_text(cur_wind.get("direct"))
                raw_wind_power = clean_text(cur_wind.get("power"))
                cur_wind_power = highlight(raw_wind_power, 8, is_gt=True, unit="")
                
                raw_wind_speed = clean_text(cur_wind.get("speed"))
                cur_wind_speed = highlight(raw_wind_speed, 25, is_gt=True, unit="m/s")

                line1 = (
                    f"<b>{name}</b> 当前天气{cur_text}{cur_icon}，"
                    f"温度{cur_temp}℃，湿度{cur_hum}%rh，"
                    f"降雨量{cur_rain}，{cur_wind_dir}{cur_wind_power}，{cur_wind_speed}。"
                )

                line2 = ""
                if len(detail) >= 2:
                    today = detail[0]
                    tomorrow = detail[1]
                    today_day = today.get("day", {})
                    today_night = today.get("night", {})
                    tomorrow_day = tomorrow.get("day", {})

                    td_w_obj = today_day.get("weather", {})
                    td_text, td_icon = get_weather_str(td_w_obj)
                    td_temp = get_temp_str(td_w_obj)
                    tn_w_obj = today_night.get("weather", {})
                    tn_text, tn_icon = get_weather_str(tn_w_obj)
                    tn_temp = get_temp_str(tn_w_obj)
                    md_w_obj = tomorrow_day.get("weather", {})
                    md_text, md_icon = get_weather_str(md_w_obj)
                    md_temp = get_temp_str(md_w_obj)

                    if td_text == "—" or td_temp == "—":
                        tn_wind = today_night.get("wind", {})
                        tn_wind_str = f"{clean_text(tn_wind.get('direct'))}{clean_text(tn_wind.get('power'))}"
                        tn_rain = clean_text(today.get("precipitation"), default="0.0")
                        md_wind = tomorrow_day.get("wind", {})
                        md_wind_str = f"{clean_text(md_wind.get('direct'))}{clean_text(md_wind.get('power'))}"
                        md_rain = clean_text(tomorrow.get("precipitation"), default="0.0")
                        line2 = (
                            f"今天夜间：{tn_temp}℃ {tn_text}{tn_icon} 降水{tn_rain}mm {tn_wind_str}，"
                            f"明天白天：{md_temp}℃ {md_text}{md_icon} 降水{md_rain}mm {md_wind_str}"
                        )
                    else:
                        td_wind = today_day.get("wind", {})
                        td_wind_str = f"{clean_text(td_wind.get('direct'))}{clean_text(td_wind.get('power'))}"
                        td_rain = clean_text(today.get("precipitation"), default="0.0")
                        tn_wind = today_night.get("wind", {})
                        tn_wind_str = f"{clean_text(tn_wind.get('direct'))}{clean_text(tn_wind.get('power'))}"
                        tn_rain = clean_text(today.get("precipitation"), default="0.0")
                        line2 = (
                            f"今天白天：{td_temp}℃ {td_text}{td_icon} 降水{td_rain}mm {td_wind_str}，"
                            f"今天夜间：{tn_temp}℃ {tn_text}{tn_icon} 降水{tn_rain}mm {tn_wind_str}"
                        )
                else:
                    line2 = "预报数据不足"
                
                city_lines.append(f"{line1}<br><span style='color:#7FD8FF;'>{line2}</span><br>")
                success_count += 1

            if success_count == len(CITIES):
                self.last_success_time = datetime.now()
                
                extra_line = "<span style='color:#888888; font-size: 16px;'>—— 数据来源于中央气象台 ——</span>"
                
                self.last_html_content = "<br><br>".join(
                    ([prov_warning_html] if prov_warning_html else []) + ["<br>".join(city_lines)] + [extra_line]
                )
                self.render_ui(force_normal_color=True)

        except Exception as e:
            print("刷新数据失败：", e)
            if not self.last_html_content:
                self.label.setText("<span style='color:#FF6B6B;'>获取数据失败，请右键刷新或检查网络...</span>")
            else:
                self.render_ui(force_normal_color=False)

    def render_ui(self, force_normal_color=False):
        now = datetime.now()
        
        is_expired = False
        if self.last_success_time is None:
            is_expired = True
        elif (now - self.last_success_time) > timedelta(hours=2):
            is_expired = True

        if force_normal_color:
            time_color = "white"
            time_str = self.last_success_time.strftime("%Y-%m-%d %H:%M") if self.last_success_time else "未知"
        else:
            time_color = "#FF6B6B" if is_expired else "white"
            time_str = self.last_success_time.strftime("%Y-%m-%d %H:%M") if self.last_success_time else "未知"

        time_header = f"<span style='color:{time_color};'>数据获取时间：{time_str}</span>"
        if is_expired and self.last_success_time:
            time_header += f" <span style='color:#FF6B6B;'>(超时未更新)</span>"

        if self.last_html_content:
            full_text = time_header + "<br><br>" + self.last_html_content
        else:
            full_text = time_header

        self.label.setText(full_text)
        self.reposition()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape: self.close()
        
    def closeEvent(self, e): 
        QApplication.quit()
        
    def contextMenuEvent(self, e):
        menu = QMenu(self)
        
        # 1. 查看雷达图菜单
        radar_menu = menu.addMenu("查看雷达图")
        
        action_nation = QAction("全国", self)
        action_nation.triggered.connect(lambda: open_in_browser("https://www.nmc.cn/publish/radar/chinaall.html"))
        radar_menu.addAction(action_nation)
        
        action_huabei = QAction("华北", self)
        action_huabei.triggered.connect(lambda: open_in_browser("https://www.nmc.cn/publish/radar/huabei.html"))
        radar_menu.addAction(action_huabei)
        
        radar_menu.addSeparator()
        
        if self.radar_links:
            for city, url in self.radar_links.items():
                action = QAction(city, self)
                action.triggered.connect(lambda checked, u=url: open_in_browser(u))
                radar_menu.addAction(action)
                
        # 2. 查看降水量菜单
        precip_menu = menu.addMenu("查看降水量")
        
        action_1h = QAction("1小时降水", self)
        action_1h.triggered.connect(lambda: open_in_browser("https://www.nmc.cn/publish/observations/hourly-precipitation.html"))
        precip_menu.addAction(action_1h)
        
        action_24h = QAction("24小时降水", self)
        action_24h.triggered.connect(lambda: open_in_browser("https://www.nmc.cn/publish/observations/24hour-precipitation.html"))
        precip_menu.addAction(action_24h)
        
        menu.addSeparator()
        
        # 3. 未来一周预报菜单
        week_menu = menu.addMenu("未来一周")
        for city_name, code in CITIES.items():
            action = QAction(city_name, self)
            action.triggered.connect(lambda checked, n=city_name, c=code: open_week_data(n, c))
            week_menu.addAction(action)

        menu.addSeparator()
        
        # 4. 查看原始数据菜单
        raw_menu = menu.addMenu("查看原始数据")
        for city_name, code in CITIES.items():
            action = QAction(city_name, self)
            action.triggered.connect(lambda checked, n=city_name, c=code: open_raw_data(n, c))
            raw_menu.addAction(action)
            
        menu.addSeparator()

        # 5. 副高分析与卫星云图
        action_subtropical = QAction("副高分析", self)
        action_subtropical.triggered.connect(lambda: open_in_browser("https://www.nmc.cn/publish/observations/china/dm/cloud-h500.htm"))
        menu.addAction(action_subtropical)
        
        action_satellite = QAction("卫星云图", self)
        action_satellite.triggered.connect(lambda: open_in_browser("https://www.nmc.cn/publish/satellite/fy4b-visible.htm"))
        menu.addAction(action_satellite)

        menu.addSeparator()

        refresh_action = QAction("立即刷新", self)
        refresh_action.triggered.connect(self.fetch)
        menu.addAction(refresh_action)
        
        menu.addSeparator()
        
        quit_action = QAction("关闭", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        
        menu.exec_(e.globalPos())
        
    def mousePressEvent(self, e):
        self.drag_pos = e.globalPos()
        
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            self.move(self.pos() + e.globalPos() - self.drag_pos)
            self.drag_pos = e.globalPos()

app = QApplication(sys.argv)
w = RainWidget()
w.show()
sys.exit(app.exec_())
