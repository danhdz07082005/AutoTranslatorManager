init -999 python:
    

    # Ensure a persistent variable exists and initialize it if needed.
    def init_persistent_var(var_name, default_value):
        if (not hasattr(persistent, var_name)) or (getattr(persistent, var_name) is None) or (not SCREEN_CONFIG):
            setattr(persistent, var_name, default_value)

    global SCREEN_CONFIG
    SCREEN_CONFIG = False

    persistent_vars = [
        # --- Visibility toggles for the floating buttons ---
        ("show_toggle_button", True),               # Show the "<<<" toggle translation button
        ("show_ocr_button", True),                  # Show the "OCR" button
        ("show_translation_settings_button", True), # Show the "Settings" button that opens the translation settings screen

        ("enable_translation", True),              # Master switch for the translation system
        ("show_comparison", False),                 # If True, display both original and translated text; otherwise only translated text
        ("language_detection_text", "Das ist ein deutscher Mustertext."), # Sample text used for automatic language detection
        ("auto_detect_language", False),             # Automatically detect target language using the sample text
        ("auto_detect_system_language", False),      #Automatically detect target language from os,only usable in PC/Linux
        ("target_languages", {                      # Language codes for each translation service
            "google":   "de",
            "bing":     "de",
            "yandex":   "de",
            "deepl":    "de",
            "freellm":  "de",
            "LLM":      "de"
        }),
        ("translation_service", "google"),          # "google", "bing", "yandex", "LLM", "freellm", "deepl",or "auto"
        ("accurate_translation_mode", False),       # Enable high-quality accurate translation (takes ~10 min for 500k texts)
        ("prescan_skip", False),                    # Skip the pre-scan phase (must be False for accurate mode)
        ("cache_only", False),                      # Use only cached translations, never call web APIs
        ("cache_target_language", False),           # Append language code to cache and glossary file names
        ("enhanced_display", False),                # Irreversibly modify the display to show translated text (toggle button will be ineffective)
        ("time_interval", 0.05),                    # Minimum seconds between web translation requests (increase for LLMs)
        ("redraw_time", 0.2),                       # Minimum seconds between redraws of translated text
        ("trans_font", "GoNotoCurrent-Regular.ttf"),# Font file to use for translated text (must be in the game folder)
        ("more_unicode_cover",True),                #Use Original Font's unicode characters ((0x0020, 0xFFFF)
        ("glossary_enabled", False),                # Enable glossary-based term replacement
        ("x_button_pos", 0.95),                     # Horizontal position of the floating buttons (0.0 - 1.0)
        ("y_button_pos", 0.05),                     # Vertical position of the floating buttons (0.0 - 1.0)
        ("save_interval", 10),                      # Seconds between automatic saves of the translation cache
        ("max_tokens", 4096),                       # Maximum response tokens for LLM queries
        ("normal_maxtexts", 100),                   # Maximum number of texts sent in one Google/Bing batch
        # LLM settings
        ("api_keys", ["Your-API-KEY1", "Your-API-KEY2"]),                      # List of API keys (will be rotated)
        ("model_name", "openai/gpt-oss-120b:free"),
        ("base_url", "https://openrouter.ai/api/v1/chat/completions"),
        # freellm settings
        ("freellm_urlindex", "random"),             # URL index for freellm: 0, 1, or "random"
        ("freellm_modellist", "random"),            # Model list selection for freellm: a list of model names or "random"
        ("temperature", 0.05),                      # LLM temperature (randomness)
        ("timeout", 60),                            # API request timeout in seconds
        ("appended_lines", 10),                     # Number of previous dialogue lines to send as context
        ("ocr_api_key", "helloworld"),              # OCR.space free API key
        ("ocr_enabled", True),                      # Enable the OCR screenshot translation feature
        ("proxies", {}),                            # HTTP proxies (cannot be changed at runtime)
        ("proxies_enabled", False),                 # Enable proxy usage
        ("dns_cache",True),                         #Enable DNS_CACHE
        ("skip_dirs", ["tl", "renpy"]),             # Directories to skip during pre-scan
        ("var_apply", True),                        # Periodically apply variable substitutions to cached translations
        ("enable_rtl", False),                      # Enable right-to-left text support
        ("last_saved_cache_size", 0),
        ("PRESCAN_FLAG", 0),
        ("accurate_mode_LLM", False),                # Use LLM (instead of freellm) for accurate mode
        ("llm_max_texts", 10),                      # Max texts per request in accurate mode
        ("accurate_urlindex", 1),                   # URL index for accurate freellm
        ("accurate_model_list", [
                    "gpt-oss-120b"
                ]),  # Models to use in accurate mode
        ("auto_accurate_interval", 1),           # Seconds between accurate re-translation batches in auto mode
        
    ]

    for var_name, default_value in persistent_vars:
        init_persistent_var(var_name, default_value)

    # Keep display_translation in sync with enable_translation
    if (not hasattr(persistent, "display_translation")) or (persistent.display_translation is None) or (not SCREEN_CONFIG):
        persistent.display_translation = persistent.enable_translation
    if persistent.translation_service=="deepl":
        if persistent.time_interval<3.05:
            persistent.time_interval=3.05
    # When accurate mode is enabled, override service settings to ensure reliability.
    if persistent.accurate_translation_mode:
        if persistent.accurate_mode_LLM:
            persistent.translation_service = "LLM"
        else:
            persistent.translation_service = "freellm"
        if persistent.time_interval < 0.4:
            persistent.time_interval = 0.4
        if persistent.save_interval > 15:
            persistent.save_interval = 15
        persistent.timeout = persistent.timeout * 2
        renpy.save_persistent()
    # Accurate mode: takes Google's HTML translation and refines it with the chosen LLM.
    def accurate_translate_batch_html(html_content, google_translated_html, text_list, speaker_map, target_lang, history_text=""):
        prompt = """You are a professional html game localization expert. 
                    CRITICAL RULES:
                    1. Preserve ALL HTML tags, attributes, and entities exactly as they are. Only translate the text content between tags.
                    2. Output ONLY the Translated HTML. Do not add any explanations or extra formatting.
                    3. TRANSLATION QUALITY:
                    - Maintain game terminology consistency.
                    - Adapt to character personalities and speech patterns.
                    - Keep dialogues natural and culturally appropriate.
                    - Preserve the original tone (humorous, serious, romantic, etc.).
                    - For UI elements, ensure clarity and conciseness.
                    - Tags MUST NOT be changed.
                    HISTORY TEXTS:
                    {0}
                    Translate the following Renpy dialogue and menu texts in HTML to {1}.
                """.format(history_text, target_lang)
        user_prompt = """HTML TO TRANSLATE:{0}""".format(html_content)
        google_hint = """
            INSTRUCTION:
            - This is a Ren'py game.
            - You can polish the existing Translated html if **NECESSARY**.
            - The HTML structure remains intact and the language is {0}.
            - Return ONLY the New Translated html, without any commentary.
            """.format(target_lang)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": "Translated html:" + google_translated_html},
            {"role": "user", "content": google_hint},
            {"role": "assistant", "content": "New Translated html:"},
        ]

        if persistent.translation_service == "LLM":
            translated_html = call_LLM_chat(messages, text_list)
        else:
            translated_html = call_freellm_chat(messages, persistent.accurate_urlindex, temperature=0.1)
        return translated_html
    # Initialize all global variables, loaders, and hook functions.
    def trans_init():
        global REQUESTS_AVAILABLE, TRANSLATION_CACHE_FILE
        global LAST_TRANSLATION_TIME, LAST_REDRAW_TIME
        global GLOSSARY_FILE, LAST_SAVE_TIME, LAST_VAR_TIME
        global glossary_dic, sorted_glossary_terms
        global tag_pattern, escape_pattern, percent_pattern, brace_pattern, escaped_char_pattern,_unified_pattern
        global bracket_pattern, link_pattern, img_pattern, input_pattern
        global source_pattern, comhtml_to_text_pattern,tag_pattern_html,unicode_escape_fix_pattern,meta_punct_pattern
        global methods, reverse_methods, auto_service_index, retry_methods, reverse_retry_methods
        global latest_font, font_groups, main_font, emoji_font
        global api_index, max_api_index
        global var_pattern
        global deepl_semaphore
        global deepl_request_count,deepl_total_time
        deepl_request_count = 0
        deepl_total_time = 0.0
        global DEEPL_LANG_MAP,complex_cache,pure_text_cache
        global deepl_content
        deepl_content="This is a Ren'py game."
        complex_cache=set()
        pure_text_cache=set()
        
        DEEPL_LANG_MAP = {
            'ar': 'ar',
            'bg': 'bg',
            'cs': 'cs',
            'da': 'da',
            'de': 'de',
            'el': 'el',
            'en': 'en',
            'en-US': 'en-US',
            'en-US': 'en-GB',
            'es': 'es',
            'es-419': 'es-419',
            'et': 'et',
            'fi': 'fi',
            'fr': 'fr',
            'hu': 'hu',
            'id': 'id',
            'it': 'it',
            'ja': 'ja',
            'ko': 'ko',
            'lt': 'lt',
            'lv': 'lv',
            'no': 'nb',   
            'nl': 'nl',
            'pl': 'pl',
            'pt': 'pt',
            'pt-BR': 'pt-BR',
            'pt-PT': 'pt-PT',
            'ro': 'ro',
            'ru': 'ru',
            'sk': 'sk',
            'sl': 'sl',
            'sv': 'sv',
            'tr': 'tr',
            'uk': 'uk',
            'zh': 'zh-Hans',
            'zh-CN': 'zh-Hans',
            'zh-TW': 'zh-Hant',
        }
        try:
            import requests
            REQUESTS_AVAILABLE = True
        except ImportError:
            import urllib2
            REQUESTS_AVAILABLE = False
            global urllib2_opener
            def get_urllib2_opener():
                import ssl
                import urllib2
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                https_handler = urllib2.HTTPSHandler(context=ssl_context) if ssl_context else urllib2.HTTPSHandler()
                if persistent.proxies_enabled and persistent.proxies:
                    proxy_handler = urllib2.ProxyHandler(persistent.proxies)
                    urllib2_opener = urllib2.build_opener(proxy_handler, https_handler)
                else:
                    urllib2_opener = urllib2.build_opener(https_handler)
                return urllib2_opener
            urllib2_opener = get_urllib2_opener()

        import re
        import os
        import threading
        deepl_semaphore = threading.Semaphore(6)
        # Select cache file location based on platform.
        if renpy.android or renpy.macintosh or renpy.linux:
            base_dir = renpy.config.savedir
            TRANSLATION_CACHE_FILE = os.path.join(base_dir, "translation_cache.json")
            GLOSSARY_FILE = os.path.join(base_dir, "glossary.json")
            if persistent.cache_target_language:
                TRANSLATION_CACHE_FILE = os.path.join(base_dir, "translation_cache_{0}.json".format(persistent.target_languages["google"]))
                GLOSSARY_FILE = os.path.join(base_dir, "glossary_{0}.json".format(persistent.target_languages["google"]))
        else:
            TRANSLATION_CACHE_FILE = "translation_cache.json"
            GLOSSARY_FILE = "glossary.json"
            if persistent.cache_target_language:
                TRANSLATION_CACHE_FILE = "translation_cache_{0}.json".format(persistent.target_languages["google"])
                GLOSSARY_FILE = "glossary_{0}.json".format(persistent.target_languages["google"])

        LAST_TRANSLATION_TIME = 0
        LAST_REDRAW_TIME = 0
        LAST_VAR_TIME = 0
        glossary_dic = {}
        sorted_glossary_terms = []
        LAST_SAVE_TIME = 0

        # Regular expressions used throughout the mod.
        var_pattern = re.compile(r'\[([^\[\]]+)\]')
        escaped_char_pattern = re.compile(r'''
            \\ (u[0-9a-fA-F]{4}| U[0-9a-fA-F]{8}| x[0-9a-fA-F]{2}| [0-7]{1,3} )
        ''', re.VERBOSE)
        tag_pattern = re.compile(r'(\s*\{[^}]*\}\s*)')
        comhtml_to_text_pattern = re.compile(r'<div id="(\d+)"[^>]*>(.*?)</div>', re.DOTALL)
        escape_pattern = re.compile(r'\\(.)')
        percent_pattern = re.compile(r'(%(?:(?:\d+|\*)?(?:\.(?:\d+|\*))?[#0\-+]?[hlL]?[bdiouxXeEfFgGcrsaHMSpTtn]|%))')
        brace_pattern = re.compile(r'(\{[^{}]*\{?[^{}]*\}?[^{}]*\})')
        bracket_pattern = re.compile(r'(\[{1,2}.*?\])')
        link_pattern = re.compile(r'<link rel="(.*?)"/>')
        img_pattern = re.compile(r'<img src="(.*?)"/>')
        source_pattern = re.compile(r'<meta name="(.*?)"/>')
        input_pattern = re.compile(r'<meta content="(.*?)"/>')
        _unified_pattern = re.compile(
                            r'(%(?:(?:\d+|\*)?(?:\.(?:\d+|\*))?[#0\-+]?[hlL]?[bdiouxXeEfFgGcrsaHMSpTtn]|%))'   # percent
                            r'|(\[[^\[\]]*\])'                    # bracket
                            r'|(\{[^{}]*\})'                      # brace
                            r'|(\\(.))'                           # escape
                        )
        tag_pattern_html = re.compile(r'<[^>]+>')
        unicode_escape_fix_pattern = re.compile(r'\\(u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|[\\\'"nrtfb]|.)')
        meta_punct_pattern = re.compile(r'(<[^>]+"/>)([.,!?;:]+)\s*(?=\n|$|<)')
        # Mapping between service indices and names.
        methods = {0: "google", 1: "bing", 2: "yandex",3:"deepl", 4: "freellm", 5: "LLM"}
        retry_methods = {0: "google", 1: "bing", 2: "yandex",3:"deepl"}
        reverse_methods = {value: key for key, value in methods.items()}
        reverse_retry_methods = {value: key for key, value in retry_methods.items()}
        auto_service_index = 0

        latest_font = "None"
        font_groups = {}
        main_font = persistent.trans_font
        emoji_font = "TwemojiCOLRv0.ttf"
        api_index = 0
        max_api_index = len(persistent.api_keys) - 1

        global len_accurate_items
        len_accurate_items = None
        renpy.save_persistent()
    def get_system_language_code():
        import locale
        import os
        lang = None
        try:
            loc = locale.getdefaultlocale()
            print(loc)
            if loc and loc[0]:
                lang = loc[0]
            else:
                raise ValueError("getdefaultlocale returned None or empty")
        except:
            pass
        if lang:
            if '.' in lang:
                lang = lang.split('.')[0]
            lang = lang.replace('_', '-')
            parts = lang.split('-')
            if len(parts) >= 2 and len(parts[1]) == 2:
                return '-'.join(parts[:2])
            return parts[0]
        for var in ('LANGUAGE', 'LC_ALL', 'LANG'):
            val = os.environ.get(var)
            if val:
                if '.' in val:
                    val = val.split('.')[0]
                val = val.replace('_', '-')
                parts = val.split('-')
                if len(parts) >= 2 and len(parts[1]) == 2:
                    return '-'.join(parts[:2])
                return parts[0]

        return None
    def auto_set_language_from_system():
        sys_lang = get_system_language_code()
        if not sys_lang:
            print("Could not detect system language.")
            return
        persistent.target_languages["google"] = sys_lang
        google_yandex_dict = {"zh-CN": "zh", "jw": "jv"}
        google_bing_dict = {"zh-CN": "zh-Hans", "sr": "sr-Cyrl", "zh-tw": "zh-Hant"}
        if sys_lang in google_yandex_dict:
            persistent.target_languages["yandex"] = google_yandex_dict[sys_lang]
        else:
            persistent.target_languages["yandex"] = sys_lang
        if sys_lang in google_bing_dict:
            persistent.target_languages["bing"] = google_bing_dict[sys_lang]
        else:
            persistent.target_languages["bing"] = sys_lang
        persistent.target_languages["freellm"] = sys_lang
        persistent.target_languages["LLM"] = sys_lang
        persistent.target_languages["deepl"] = sys_lang
        renpy.save_persistent()
        print("System language detected:", sys_lang)
        print("Updated target languages:", persistent.target_languages)
    def _unified_replace(match):
        percent, bracket, brace, escape_full, escape_char = match.groups()
        if percent is not None:
            return '<img src="{}"/>'.format(html_escape(percent, quote=True))
        if bracket is not None:
            return '<meta content="{}"/>'.format(html_escape(bracket, quote=True))
        if brace is not None:
            return '<meta name="{}"/>'.format(html_escape(brace, quote=True))
        if escape_full is not None:
            if escape_char in ('\\', '"', "'", ' ', '%', '&', 'u', 'U', 'x', 'X'):
                return escape_full  
            return '<link rel="\\{}"/>'.format(escape_char)
        return match.group(0)  
    # Automatically detect the target language using Google Translate and update all service codes.
    def detect_language_from_text(text):
        import json, random, uuid, re

        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": "en",
                "dt": "t",
                "q": text
            }
            if REQUESTS_AVAILABLE:
                import requests as req_lib
                session = session_manager.get_session()
                resp = session.get(url, params=params,proxies=session_manager._current_proxies, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if len(data) > 2 and data[2]:
                        persistent.target_languages["google"] = data[2]
            else:
                import urllib2 as urllib_lib
                import urllib as urlparse
                full_url = url + "?" + urlparse.urlencode(params)
                req = urllib_lib.Request(full_url)
                global urllib2_opener
                response = urllib2_opener.open(req, timeout=10)
                data = json.loads(response.read())
                if len(data) > 2 and data[2]:
                    persistent.target_languages["google"] = data[2]
        except Exception as e:
            print("Google detect failed:", e)

        # Update language codes for other services based on the detected Google code.
        google_yandex_dict = {"zh-CN": "zh", "jw": "jv"}
        google_bing_dict = {"zh-CN": "zh-Hans", "sr": "sr-Cyrl", "zh-tw": "zh-Hant"}
        if persistent.target_languages["google"] in google_yandex_dict:
            persistent.target_languages["yandex"] = google_yandex_dict[persistent.target_languages["google"]]
        else:
            persistent.target_languages["yandex"] = persistent.target_languages["google"]
        if persistent.target_languages["google"] in google_bing_dict:
            persistent.target_languages["bing"] = google_bing_dict[persistent.target_languages["google"]]
        else:
            persistent.target_languages["bing"] = persistent.target_languages["google"]
        persistent.target_languages["freellm"] = persistent.target_languages["google"]
        persistent.target_languages["LLM"] = persistent.target_languages["google"]
        persistent.target_languages["deepl"]=persistent.target_languages["google"]
        renpy.save_persistent()
        print("Translate api language codes", persistent.target_languages)

    # Load the glossary from its JSON file.
    def load_glossary():
        global sorted_glossary_terms, glossary_dic
        import json
        try:
            try:
                with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
                    glossary_dic = json.load(f)
            except:
                import codecs
                with codecs.open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
                    glossary_dic = json.load(f)
            sorted_glossary_terms = sorted(glossary_dic.keys(), key=len, reverse=True)
            apply_glossary_patterns()
        except:
            sorted_glossary_terms = []

    # Add a new term to the glossary and save it.
    def add_glossary_entry(original, translation):
        global glossary_dic, sorted_glossary_terms
        if not original or not translation:
            return False
        glossary_dic[original] = translation
        if original not in sorted_glossary_terms:
            sorted_glossary_terms.append(original)
            sorted_glossary_terms = sorted(sorted_glossary_terms, key=len, reverse=True)
        apply_glossary_patterns()
        import json
        try:
            try:
                with open(GLOSSARY_FILE, "w", encoding="utf-8") as f:
                    json.dump(glossary_dic, f, ensure_ascii=False, indent=2)
                return True
            except:
                import codecs
                with codecs.open(GLOSSARY_FILE, "w", encoding="utf-8") as f:
                    json.dump(glossary_dic, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error saving glossary:", str(e))
            return False

    # Load the translation cache from disk.
    def load_translation_cache():
        import json
        try:
            try:
                with open(TRANSLATION_CACHE_FILE, "r", encoding="utf-8") as f:
                    raw_cache = json.load(f)
            except:
                import codecs
                with codecs.open(TRANSLATION_CACHE_FILE, "r", encoding="utf-8") as f:
                    raw_cache = json.load(f)
            mdata.translation_cache = {}
            for key, value in raw_cache.items():
                if key != value:
                    mdata.translation_cache[key] = value
                    mdata.translated_set.add(value)
                    if r'[' in key and r']' in key:
                        mdata.var_set.add(key)
            persistent.last_saved_cache_size = len(mdata.translation_cache)
        except:
            mdata.translation_cache = {}
            persistent.last_saved_cache_size = 0
        try:
            renpy.save_persistent()
        except Exception as e:
            print("Error saving persistent data:", str(e))
        return

    # Safely predict the text of a translate object.
    def safe_predict(tl):
        try:
            return tl.predict()[0]
        except Exception as e:
            return None

    # Process a Say node and collect its text for pre-scanning.
    def process_say_node(node):
        try:
            text_content = node.what
            if node.who is not None:
                try:
                    chara = renpy.ast.eval_who(node.who)
                    text_content = chara.prefix_suffix("what", chara.what_prefix, text_content, chara.what_suffix)
                except Exception:
                    pass
            if ((text_content not in mdata.translation_cache) and
                (text_content not in mdata.PRESCAN_TEXTS) and
                (len(text_content) > 1)):
                mdata.PRESCAN_TEXTS.add(text_content)
        except Exception:
            pass

    # Extract the text content from a menu item label.
    def process_menu_text(text):
        try:
            if isinstance(text, str) or isinstance(text, basestring):
                return text
            elif isinstance(text, tuple):
                if text and isinstance(text[0], str):
                    return text[0]
            elif hasattr(text, 'expression'):
                try:
                    result = renpy.python.py_eval(text.expression)
                    if isinstance(result, str):
                        return result
                except:
                    pass
            elif hasattr(text, 'w'):
                return text.w
        except:
            pass
        return ""

    # Process a Menu node and collect its title and choices for pre-scanning.
    def process_menu_node(node):
        try:
            if hasattr(node, 'title') and node.title is not None:
                title_text = process_menu_text(node.title)
                if title_text and ((title_text not in mdata.translation_cache) and(title_text not in mdata.PRESCAN_TEXTS) and(len(title_text) > 1)):
                    mdata.PRESCAN_TEXTS.add(title_text)

            for item in node.items:
                if len(item) >= 3:
                    label = item[0]
                    label_text = process_menu_text(label)
                    if label_text and ((label_text not in mdata.translation_cache) and (label_text not in mdata.PRESCAN_TEXTS) and (len(label_text) > 1)):
                        mdata.PRESCAN_TEXTS.add(label_text)
        except Exception:
            pass

    # Recursively find all Menu nodes inside an AST block.
    def find_menus_in_statement(stmt, collected_menus):
        if isinstance(stmt, renpy.ast.Menu):
            collected_menus.append(stmt)
        if hasattr(stmt, 'block') and stmt.block:
            if isinstance(stmt.block, (list, tuple)):
                for sub_stmt in stmt.block:
                    if sub_stmt:
                        find_menus_in_statement(sub_stmt, collected_menus)
        if hasattr(stmt, 'entries') and stmt.entries:
            for entry in stmt.entries:
                if hasattr(entry, 'block') and entry.block:
                    for sub_stmt in entry.block:
                        if sub_stmt:
                            find_menus_in_statement(sub_stmt, collected_menus)

    # Gather every menu node in the entire script.
    def collect_all_menu_nodes():
        all_menu_nodes = []
        for name, item in renpy.game.script.namemap.items():
            if isinstance(item, (renpy.ast.Label, renpy.ast.Translate)):
                find_menus_in_statement(item, all_menu_nodes)
        return all_menu_nodes

    # Walk the AST and collect Say/Menu nodes and other text strings.
    def collect_all_text_nodes(root_node):
        import re
        say_menu_nodes = []
        other_texts = set()

        def add_text_from_attrs(node):
            for attr in ('text', 'label', 'title', 'caption'):
                try:
                    val = getattr(node, attr, None)
                    if isinstance(val, str) and val:
                        other_texts.add(val)
                except Exception:
                    pass

        def extract_strings_from_code(code):
            strings = set()
            for m in re.finditer(r'\("((?:[^"\\]|\\.)*)"\)', code):
                if m.group(1):
                    strings.add(m.group(1))
            for m in re.finditer(r"\('((?:[^'\\]|\\.)*)'\)", code):
                if m.group(1):
                    strings.add(m.group(1))
            return strings

        import os

        def _walk(node):
            try:
                if node is None:
                    return
                try:
                    filepath = os.path.normpath(node.filename)
                    if any(filepath.startswith(d + os.sep) for d in persistent.skip_dirs):
                        return
                except Exception:
                    pass
                if os.path.basename(node.filename) in ["realtimetrans.rpy", "transconfig.rpy", "useragentlist.rpy"]:
                    return
                if isinstance(node, (renpy.ast.Say, renpy.ast.Menu)):
                    say_menu_nodes.append(node)
                add_text_from_attrs(node)
                if isinstance(node, renpy.ast.Python):
                    try:
                        code = node.code.source
                        other_texts.update(extract_strings_from_code(code))
                    except Exception:
                        pass
                if hasattr(node, 'block') and node.block:
                    for stmt in node.block:
                        try:
                            _walk(stmt)
                        except:
                            pass
                if isinstance(node, renpy.ast.Menu):
                    for item in node.items:
                        if isinstance(item, (list, tuple)) and len(item) >= 3:
                            maybe_block = item[2]
                            if isinstance(maybe_block, (list, tuple)):
                                for stmt in maybe_block:
                                    try:
                                        _walk(stmt)
                                    except:
                                        pass
                        if hasattr(item, 'block') and item.block:
                            for stmt in item.block:
                                try:
                                    _walk(stmt)
                                except:
                                    pass
            except:
                pass

        _walk(root_node)
        return say_menu_nodes, list(other_texts)

    # Optimized version of process_menu_node used during pre-scan.
    def process_menu_node_optimized(node):
        try:
            if hasattr(node, 'title') and node.title is not None:
                title_text = process_menu_text(node.title)
                if title_text and len(title_text) > 1:
                    if (title_text not in mdata.translation_cache and
                        title_text not in mdata.PRESCAN_TEXTS):
                        mdata.PRESCAN_TEXTS.add(title_text)
            for item in node.items:
                if len(item) >= 3:
                    label = item[0]
                    label_text = process_menu_text(label)
                    if label_text and len(label_text) >= 1:
                        if (label_text not in mdata.translation_cache and
                            label_text not in mdata.PRESCAN_TEXTS):
                            mdata.PRESCAN_TEXTS.add(label_text)
        except Exception:
            pass

    # Main pre-scan: collect all game texts and optionally prepare accurate mode lists.
    def prerun():
        import time

        try:
            _renpy_translator = renpy.game.script.translator
            time.sleep(0.1)
            print("Starting pre-scan at time: ", renpy.time.time())

            all_nodes = []
            all_python_texts = set()

            print("Collecting nodes and Python _() strings via AST parsing...")
            for name, node in list(renpy.game.script.namemap.items()):
                nodes, py_texts = collect_all_text_nodes(node)
                all_nodes.extend(nodes)
                all_python_texts.update(py_texts)
            print("Collecting nodes from translate objects...")
            for tl in list(_renpy_translator.default_translates.values()):
                node = safe_predict(tl)
                if node:
                    all_nodes.append(node)
            all_nodes = list(set(all_nodes))
            all_nodes.sort(key=lambda n: (n.filename, n.linenumber) if hasattr(n, 'filename') and hasattr(n, 'linenumber') else ("", 0))
            all_python_texts = list(set(all_python_texts))
            print(len(all_nodes), " AST nodes to pre-scan")
            print(len(all_python_texts), " Python _() strings found")
            all_nodes_len = len(all_nodes)//50//10*10
            say_count = 0
            menu_count = 0
            processed_count = 0
            accurate_items = [] if persistent.accurate_translation_mode else None
            for counter, node in enumerate(all_nodes):
                if isinstance(node, renpy.ast.Say):
                    text_content = node.what
                    if node.who is not None:
                        try:
                            chara = renpy.ast.eval_who(node.who)
                            text_content = chara.prefix_suffix("what", chara.what_prefix, text_content, chara.what_suffix)
                        except Exception:
                            pass
                    speaker = ""
                    if node.who is not None:
                        try:
                            who_obj = renpy.ast.eval_who(node.who)
                            if hasattr(who_obj, 'name') and who_obj.name:
                                speaker = who_obj.name
                            else:
                                speaker = str(who_obj)
                        except Exception:
                            speaker = str(node.who)
                    if text_content and len(text_content) > 1:
                        if (text_content not in mdata.translation_cache and
                            text_content not in mdata.PRESCAN_TEXTS):
                            mdata.PRESCAN_TEXTS.add(text_content)

                    if persistent.accurate_translation_mode and text_content and len(text_content.strip()) >= 1:
                        if text_content not in mdata.translation_cache:
                            accurate_items.append((text_content, speaker))

                    say_count += 1
                    processed_count += 1

                elif isinstance(node, renpy.ast.Menu):
                    process_menu_node_optimized(node)
                    menu_count += 1
                    processed_count += 1

                if counter % all_nodes_len == 0 and counter > all_nodes_len:
                    print("Pre-scanned ", counter)

            python_text_count = 0
            for text in all_python_texts:
                if not text or len(text.strip()) < 1:
                    continue
                if text not in mdata.translation_cache and text not in mdata.PRESCAN_TEXTS:
                    mdata.PRESCAN_TEXTS.add(text)
                    python_text_count += 1
                    if persistent.accurate_translation_mode:
                        accurate_items.append((text, ""))

            print("\n" + "="*50)
            print("Pre-scan complete!")
            mdata.prescan_texts = list(mdata.PRESCAN_TEXTS)
            print("prescan_texts len is ", len(mdata.prescan_texts))
            print("Added {} Python _() strings.".format(python_text_count))
            if persistent.accurate_translation_mode:
                mdata.accurate_pending_items = accurate_items
                mdata.accurate_full_list = list(accurate_items)
                idx_map = {}
                for i, item in enumerate(accurate_items):
                    if item[0] not in idx_map:
                        idx_map[item[0]] = i
                mdata.accurate_text_to_idx = idx_map
                global len_accurate_items
                len_accurate_items = len(accurate_items) + len(mdata.translation_cache)
                print("Accurate mode collected {} items for translation.".format(len_accurate_items))
            print("="*50)
            renpy.save_persistent()
        except Exception as e:
            print("Error during pre-scan: ", e)

    # Save the current translation cache to disk if it has grown.
    def save_translation_cache():
        import json
        try:
            current_size = len(mdata.translation_cache)
            if persistent.enable_translation and persistent.display_translation:
                if current_size >= persistent.last_saved_cache_size:
                    if current_size - persistent.last_saved_cache_size >= 1:
                        try:
                            translation_cache_tmp = mdata.translation_cache.copy()
                            with open(TRANSLATION_CACHE_FILE, "w", encoding="utf-8") as f:
                                json.dump(translation_cache_tmp, f, ensure_ascii=False, indent=2)
                        except:
                            import codecs
                            translation_cache_tmp = mdata.translation_cache.copy()
                            with codecs.open(TRANSLATION_CACHE_FILE, "w", encoding="utf-8") as f:
                                json.dump(translation_cache_tmp, f, ensure_ascii=False, indent=2)
                        persistent.last_saved_cache_size = max(current_size, persistent.last_saved_cache_size)
                        renpy.save_persistent()
                        return True
                    else:
                        return False
                else:
                    print("Translation cache size decreased, reloading cache...")
                    load_translation_cache()
                    return False
        except:
            return False

    # Register a text displayable that needs redrawing when its translation arrives.
    def add_text_object_to_redraw(text_content, text_obj):
        if text_content not in mdata.TEXT_OBJECTS_TO_REDRAW:
            mdata.TEXT_OBJECTS_TO_REDRAW[text_content] = set()
        mdata.TEXT_OBJECTS_TO_REDRAW[text_content].add(text_obj)

    def get_text_objects_for_redraw(text_content):
        if text_content in mdata.TEXT_OBJECTS_TO_REDRAW:
            return list(mdata.TEXT_OBJECTS_TO_REDRAW[text_content])
        return []

    def remove_text_content_from_redraw(text_content):
        if text_content in mdata.TEXT_OBJECTS_TO_REDRAW:
            del mdata.TEXT_OBJECTS_TO_REDRAW[text_content]

    def cleanup_empty_sets():
        to_delete = [
            key for key, weak_set in list(mdata.TEXT_OBJECTS_TO_REDRAW.items())
            if len(weak_set) == 0 or len(key) < 3
        ]
        for key in to_delete:
            del mdata.TEXT_OBJECTS_TO_REDRAW[key]

    # Select texts for accurate mode translation, honoring the character limit.
    def get_accurate_texts_to_translate(PENDING_TRANSLATIONS_copy, max_chars=None):
        import random
        import time
        if max_chars is None:
            max_chars = int(persistent.max_tokens * 0.2) + random.randint(50, 100)
        acc_items_snapshot = list(mdata.accurate_pending_items)
        text_to_speaker = {text: speaker for text, speaker in acc_items_snapshot}
        runtime_texts = list(PENDING_TRANSLATIONS_copy.keys())
        selected_texts = []
        selected_speakers = []
        current_chars = 0
        runtime_len = len(runtime_texts)
        for i, text in enumerate(runtime_texts):
            if text is not None:
                if current_chars + len(text) <= max_chars:
                    selected_texts.append(text)
                    speaker = text_to_speaker.get(text, "unknown")
                    selected_speakers.append(speaker)
                    current_chars += len(text)
                    if len(selected_texts) >= persistent.llm_max_texts:
                        for remaining_text in runtime_texts[i+1:]:
                            mdata.PENDING_TRANSLATIONS[remaining_text] = None
                        break
                else:
                    if i == 0:
                        selected_texts.append(text)
                        speaker = text_to_speaker.get(text, "unknown")
                        selected_speakers.append(speaker)
                        current_chars += len(text)
                    for remaining_text in runtime_texts[i+1:]:
                        mdata.PENDING_TRANSLATIONS[remaining_text] = None
                    break

        selected_set = set(selected_texts)
        acc_snapshot = list(mdata.accurate_pending_items)
        new_acc_items = [item for item in acc_snapshot if item[0] not in selected_set]
        mdata.accurate_pending_items = new_acc_items
        batch_history = []
        if selected_texts and mdata.accurate_full_list:
            first_text = selected_texts[0]
            idx = mdata.accurate_text_to_idx.get(first_text, -1)
            if idx != -1:
                start = max(0, idx - 10)
                context_items = mdata.accurate_full_list[start:idx]
                batch_history = [
                    "{0}: {1}".format(item[1], item[0]) if item[1] else item[0]
                    for item in context_items
                ]
        return selected_texts, selected_speakers, batch_history

    # Select texts for standard translation, possibly mixing pending and prescan texts.
    def get_texts_to_translate(PENDING_TRANSLATIONS_copy, translate_service):
        import random
        runtime_texts = list(PENDING_TRANSLATIONS_copy.keys())
        runtime_count = len(runtime_texts)
        ALL_PENDING_FLAG = 0
        try:
            if len(mdata.prescan_texts) == 0:
                ALL_PENDING_FLAG = 1
                if runtime_count==0:
                    return runtime_texts
            if random.randint(0,2)<1:
                runtime_texts=runtime_texts[::-1]
            if translate_service == "freellm" or translate_service == "LLM" or translate_service == "yandex" or translate_service == "deepl":
                max_chars = int(persistent.max_tokens * 0.3) + random.randint(0, 5)
                max_texts=persistent.llm_max_texts
                if translate_service == "deepl":
                    max_chars=1400
                    max_texts=persistent.normal_maxtexts
                runtime_len = len(runtime_texts)
                current_chars = 0
                selected_texts = []
                for i, text in enumerate(runtime_texts):
                    if text is not None:
                        if current_chars + len(text) <= max_chars:
                            selected_texts.append(text)
                            
                            if translate_service == "deepl":
                                combined_html,original_texts = text_to_comhtml([text])
                                current_chars +=len(combined_html)
                            else:
                                current_chars += len(text)
                            if len(selected_texts) >= max_texts:
                                for remaining_text in runtime_texts[i+1:]:
                                    mdata.PENDING_TRANSLATIONS[remaining_text] = None
                                break
                        else:
                            if i == 0:
                                selected_texts.append(text)
                            for remaining_text in runtime_texts[i+1:]:
                                mdata.PENDING_TRANSLATIONS[remaining_text] = None
                            break
                if ALL_PENDING_FLAG == 0 and current_chars < max_chars and len(selected_texts)<max_texts:
                    remaining_chars = max_chars - current_chars
                    remaining_prescan = []
                    
                    prescan_snapshot = list(mdata.prescan_texts)
                    for i, text in enumerate(prescan_snapshot):
                        if text is not None:
                            if len(text) <= remaining_chars:
                                selected_texts.append(text)
                                
                                if translate_service == "deepl":
                                    combined_html,original_texts = text_to_comhtml([text])
                                    remaining_chars -=len(combined_html)
                                else:
                                    remaining_chars -= len(text)
                            else:
                                remaining_prescan = mdata.prescan_texts[i:]
                                break
                    mdata.prescan_texts = remaining_prescan
                texts_to_translate = selected_texts
            else:
                max_texts = persistent.normal_maxtexts
                
                if runtime_count >= max_texts:
                    ALL_PENDING_FLAG = 1
                texts_to_translate = runtime_texts[:max_texts]
                for remaining_text in runtime_texts[max_texts+1:]:
                    mdata.PENDING_TRANSLATIONS[remaining_text] = None
                
                if ALL_PENDING_FLAG == 0:
                    remaining = max_texts - runtime_count
                    if remaining > 0:
                        if len(mdata.prescan_texts) > remaining:
                            selected_prescan = mdata.prescan_texts[:remaining]
                            mdata.prescan_texts = mdata.prescan_texts[remaining:]
                            texts_to_translate.extend(selected_prescan)
                        else:
                            texts_to_translate.extend(mdata.prescan_texts)
                            mdata.prescan_texts = []        
            texts_to_translate_final = []
            for text in texts_to_translate:
                if text not in mdata.translation_cache:
                    texts_to_translate_final.append(text)
            return texts_to_translate_final
        except Exception as e:
            print("get_texts_to_translate error", e)
            return runtime_texts
    def deepl_get_texts_to_translate(PENDING_TRANSLATIONS_copy, translate_service):
        import random
        runtime_texts = list(PENDING_TRANSLATIONS_copy.keys())
        runtime_count = len(runtime_texts)
        ALL_PENDING_FLAG = 0
        global _unified_pattern,complex_cache,pure_text_cache
        
        try:
            if len(mdata.prescan_texts) == 0:
                ALL_PENDING_FLAG = 1
                if runtime_count==0:
                    return runtime_texts
            all_candidate_texts = list(set(runtime_texts + mdata.prescan_texts))  
            remaining_prescan = []
            for t in all_candidate_texts:
                if t is not None and  bool(_unified_pattern.search(t)):
                    complex_cache.add(t)
                else:
                    if len(t)<1350:
                        pure_text_cache.add(t)
                    else:
                        complex_cache.add(t)
            if random.randint(0,2)<1:
                runtime_texts=runtime_texts[::-1]
            selected_texts = []
            if translate_service == "deepl":
                max_chars=1350
                max_texts=50
                runtime_len = len(runtime_texts)
                current_chars = 0
                
                for i, text in enumerate(runtime_texts):
                    if text is not None:
                        if text in pure_text_cache:
                            if current_chars + len(text) <= max_chars :
                                selected_texts.append(text)
                                current_chars += len(text)
                                if len(selected_texts) >= max_texts:
                                    for remaining_text in runtime_texts[i+1:]:
                                        mdata.PENDING_TRANSLATIONS[remaining_text] = None
                                    break
                            else:
                                if len(selected_texts)== 0 :
                                    complex_cache.add(text)
                                for remaining_text in runtime_texts[i+1:]:
                                    mdata.PENDING_TRANSLATIONS[remaining_text] = None
                                break
                if ALL_PENDING_FLAG == 0 and current_chars < max_chars and len(selected_texts)<max_texts:
                    remaining_chars = max_chars - current_chars                  
                    prescan_snapshot = list(mdata.prescan_texts)
                    for i, text in enumerate(prescan_snapshot):
                        if text is not None:
                            if text in pure_text_cache:
                                if len(text) <= remaining_chars:
                                    selected_texts.append(text)
                                    remaining_chars -= len(text)
                                else:
                                    remaining_prescan.extend(prescan_snapshot[i:])
                                    break
                            else:
                                remaining_prescan.append(text)
                    mdata.prescan_texts = remaining_prescan
                texts_to_translate = selected_texts
            else:
                max_texts = persistent.normal_maxtexts
                for i, text in enumerate(runtime_texts):
                    if text is not None:
                        if text in complex_cache:
                            selected_texts.append(text)
                            if len(selected_texts) >= max_texts:
                                for remaining_text in runtime_texts[i+1:]:
                                    mdata.PENDING_TRANSLATIONS[remaining_text] = None
                                break            
                if ALL_PENDING_FLAG == 0:
                    remaining = max_texts - len(selected_texts)
                    prescan_snapshot = list(mdata.prescan_texts)
                    if remaining > 0:                        
                        for i, text in enumerate(prescan_snapshot):
                            if text is not None:
                                if text in complex_cache:
                                    if len(selected_texts)<max_texts:
                                        selected_texts.append(text)
                                    else:
                                        remaining_prescan.extend(prescan_snapshot[i:])
                                        break
                                else:
                                    remaining_prescan.append(text)
                        mdata.prescan_texts = remaining_prescan 
                texts_to_translate = selected_texts    
            texts_to_translate_final = []
            for text in texts_to_translate:
                if text not in mdata.translation_cache:
                    texts_to_translate_final.append(text)
            return texts_to_translate_final
        except Exception as e:
            print("get_texts_to_translate error", e)
            return runtime_texts
    # Attempt translation with one service; retry with fallbacks on failure.
    def translation_thread(texts_to_translate, translation_service0=persistent.translation_service):
        for failed_times in range(5):
            if failed_times > 0:
                if failed_times >= 3:
                    print("all method failed")
                    for text in texts_to_translate:
                        mdata.PENDING_TRANSLATIONS[text] = None
                    return
                else:
                    if  translation_service0=="deepl":
                        for text in texts_to_translate:
                            mdata.PENDING_TRANSLATIONS[text] = None
                        return
                    if  translation_service0 != "freellm" and translation_service0 != "LLM" :
                        translation_service = retry_methods[(reverse_methods[translation_service0] + failed_times) % 3]
                    if  translation_service=="deepl":
                        translation_service = retry_methods[(reverse_methods[translation_service0] + failed_times+1) % 3]


            else:
                translation_service = translation_service0
            try:
                translations = translate_batch(texts_to_translate, persistent.target_languages[translation_service], translation_service)
                if (translation_service == "freellm") or (translation_service == "LLM"):
                    return
            except Exception as e:
                print(str(e))
                continue
            if translations != texts_to_translate and translations != {}:
                break
        if isinstance(translations, dict):
            process_translation_results(translations)
            if persistent.translation_service == "auto" and translation_service0 != "freellm":
                for original, translated in translations.items():
                    mdata.auto_pending_accurate[original] = translated

    # Return active proxy settings.
    def get_proxies():
        return persistent.proxies if persistent.proxies_enabled else None
    def _normalize_deepl_lang(target_lang):
        global DEEPL_LANG_MAP
        
        if (not target_lang) or (target_lang not in DEEPL_LANG_MAP):
            return "noway"
        return DEEPL_LANG_MAP.get(target_lang, target_lang)
    def _send_batch_translation_request_deepl_texts(texts_list, target_lang):
        import json, random
        global deepl_request_count, deepl_total_time
        global deepl_content
        try:
            url = "https://oneshot-free.www.deepl.com/v1/translate"
            headers = {
                "Accept": "*/*",
                "Authorization": "None",
                "Content-Type": "application/json",
                "Origin": "chrome-extension://cofdbpoegempjloogbagkncekinflcnj",
                "Priority": "u=1, i",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "none",
                "User-Agent": "DeepLBrowserExtension/1.95.0"+random.choice(USER_AGENTS),
            }
            payload = {
                "text": texts_list,          
                "target_lang": target_lang, 
                "UsageType" :  "Translate",
                "model_type":  "quality_optimized",
                "content":  deepl_content
            }
            session = session_manager.get_session()
            global deepl_semaphore
            with deepl_semaphore:
                start_time = renpy.time.time()
                response = session.post(
                    url,
                    headers=headers,
                    json=payload,
                    proxies=session_manager._current_proxies,
                    timeout=30,
                )
                end_time = renpy.time.time()
            deepl_request_count += 1
            deepl_total_time += end_time - start_time
            print(deepl_request_count,"response time",end_time-start_time," ",deepl_total_time/deepl_request_count)
            if response.status_code == 200:
                result = response.json()
                translations = result.get("translations", [])
                if translations:
                    return [item.get("text", "") for item in translations]
            else:
                print("DeepL texts failed ", response.status_code, response.text)
                print("deepl failed ori",texts_list,len(texts_list))
        except Exception as e:
            print("DeepL texts request failed: {}".format(str(e)))
        return texts_list  

    def _send_batch_translation_request_deepl_texts_urllib2(texts_list, target_lang):
        import json, random, urllib2
        global deepl_content
        try:
            url = "https://oneshot-free.www.deepl.com/v1/translate"
            headers = {
                "Accept": "*/*",
                "Authorization": "None",
                "Content-Type": "application/json",
                "Origin": "chrome-extension://cofdbpoegempjloogbagkncekinflcnj",
                "Priority": "u=1, i",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "none",
                "User-Agent": "DeepLBrowserExtension/1.95.0" + random.choice(USER_AGENTS),
            }
            payload = {
                "text": texts_list,          
                "target_lang": target_lang, 
                "UsageType" :  "Translate",
                "model_type":  "quality_optimized",
                "content":  deepl_content
            }
            global urllib2_opener
            req = urllib2.Request(url, json.dumps(payload), headers)
            global deepl_semaphore
            with deepl_semaphore:
                response = urllib2_opener.open(req, timeout=30)
            result = json.loads(response.read())
            translations = result.get("translations", [])
            if translations:
                return [item.get("text", "") for item in translations]
        except Exception as e:
            print("DeepL urllib2 texts request failed: {}".format(str(e)))
        return texts_list
    def _send_batch_translation_request_deepl(texts, target_lang):
        import json
        import random
        global deepl_request_count,deepl_total_time,deepl_content
        language_code_deepl=_normalize_deepl_lang(target_lang)
        if language_code_deepl=="noway":
            return texts
        try:
            url = "https://oneshot-free.www.deepl.com/v1/translate"

            headers = {
                "Accept": "*/*",
                "Authorization": "None",
                "Content-Type": "application/json",
                "Origin": "chrome-extension://cofdbpoegempjloogbagkncekinflcnj",
                "Priority": "u=1, i",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "none",
                "User-Agent": "DeepLBrowserExtension/1.95.0"+random.choice(USER_AGENTS),
            }
            payload = {
                "text": [texts],
                "target_lang": language_code_deepl,
                "tag_handling":"html",
                "tag_handling_version": "v2",
                "UsageType" :  "Translate",
                "model_type":  "quality_optimized",
                "content":  deepl_content
            }
            session = session_manager.get_session()
            global deepl_semaphore
            with deepl_semaphore:
                start_time=renpy.time.time()
                response = session.post(
                    url,
                    headers=headers,
                    json=payload,
                    proxies=session_manager._current_proxies,
                    timeout=30,
                )
            end_time=renpy.time.time()
            deepl_request_count+=1
            deepl_total_time+=end_time-start_time
            #print(deepl_request_count,"response time",end_time-start_time," ",deepl_total_time/deepl_request_count)
            if response.status_code == 200:
                result = response.json()
                translations = result.get("translations", [])
                if translations:
                    return translations[0].get("text", "")
            else:
                print("DeepL failed ", response.status_code, response.text)
        except Exception as e:
            print("DeepL request failed: {}".format(str(e)))
        return texts
    def _send_batch_translation_request_deepl_urllib2(texts, target_lang):
        import json
        import random
        import urllib2
        global deepl_content
        language_code_deepl=_normalize_deepl_lang(target_lang)
        if language_code_deepl=="noway":
            return texts
        try:
            url = "https://oneshot-free.www.deepl.com/v1/translate"
            headers = {
                "Accept": "*/*",
                "Authorization": "None",
                "Content-Type": "application/json",
                "Origin": "chrome-extension://cofdbpoegempjloogbagkncekinflcnj",
                "Priority": "u=1, i",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "none",
                "User-Agent": "DeepLBrowserExtension/1.95.0"+random.choice(USER_AGENTS),
            }
            payload = {
                "text": [texts],
                "target_lang": language_code_deepl,
                "tag_handling":"html",
                "tag_handling_version": "v2",
                "UsageType" :  "Translate",
                "model_type":  "quality_optimized",
                "content":  deepl_content
            }
            global urllib2_opener
            req = urllib2.Request(url, json.dumps(payload), headers)
            global deepl_semaphore
            with deepl_semaphore:
                response = urllib2_opener.open(req, timeout=30)
                result = json.loads(response.read())
            translations = result.get("translations", [])
            if translations:
                return translations[0].get("text", "")
        except Exception as e:
            print("DeepL urllib2 request failed: {}".format(str(e)))
        return texts
    # Send a batch to the Google HTML translate API (requests version).
    def _send_batch_translation_request_requests(html_content, target_lang):
        try:
            import random
            api_key = ""
            url = "https://translate-pa.googleapis.com/v1/translateHtml"
            headers = {
                "Accept": "/",
                "Content-Type": "application/json+protobuf",
                "User-Agent": random.choice(USER_AGENTS),
                "X-Goog-API-Key": api_key,
                "model": "nmt",
                "priority": "u=1, i"
            }
            data = [
                [html_content, "auto", target_lang],
                "te_lib"
            ]
            session = session_manager.get_session()
            response = session.post(
                url,
                headers=headers,
                json=data,
                proxies=session_manager._current_proxies,
                timeout=20,
            )
            response.raise_for_status()
            result = response.json()
            
            return result[0][0]
        except Exception as e:
            pass

    # Send a batch to the Google HTML translate API (urllib2 version).
    def _send_batch_translation_request_urllib2(html_content, target_lang):
        import json
        import random
        import urllib2
        api_key = "AIzaSyATBXajvzQLTDHEQbcpq0Ihe0vWDHmO520"
        url = "https://translate-pa.googleapis.com/v1/translateHtml"
        headers = {
            "Accept": "/",
            "Content-Type": "application/json+protobuf",
            "User-Agent": random.choice(USER_AGENTS),
            "X-Goog-API-Key": api_key,
            "model": "nmt",
            "priority": "u=1, i"
        }
        data = [
            [html_content, "auto", target_lang],
            "te_lib"
        ]
        req = urllib2.Request(url, json.dumps(data), headers)
        try:
            global urllib2_opener
            opener = urllib2_opener
            response = opener.open(req, timeout=20)
            raw_content = response.read()
            return result
        except Exception as e:
            print("Request failed: {}".format(str(e)))
            raise

    # Format a list of chat messages into a single string for the API.
    def format_prompt(messages, add_special_tokens=False, do_continue=False, include_system=True):
        def to_string(value):
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                if "text" in value:
                    return value.get("text", "")
                return ""
            elif isinstance(value, list):
                result = ""
                for v in value:
                    result += to_string(v)
                return result
            elif value is None:
                return ""
            else:
                return str(value)
        if not add_special_tokens and len(messages) <= 1:
            if messages and "content" in messages[0]:
                return to_string(messages[0]["content"])
            return ""
        processed_messages = []
        for message in messages:
            if "role" in message and "content" in message:
                if include_system or message.get("role") != "system":
                    content_str = to_string(message["content"])
                    if content_str and content_str.strip():
                        processed_messages.append((message["role"], content_str))
        if not processed_messages:
            return ""
        formatted_parts = []
        for role, content in processed_messages:
            role_capitalized = role.capitalize()
            formatted_parts.append("{role}: {content}".format(role=role_capitalized, content=content))
        formatted = "\n".join(formatted_parts)
        if do_continue:
            return formatted
        return formatted + "\nAssistant:"

    # Retrieve the last few dialogue lines as context for the LLM.
    def get_previous_dialogue():
        previous_dialogue = []
        for h in _history_list[-persistent.appended_lines:]:
            try:
                dialogues_content = "{0}:{1}".format(h.who, h.what)
                previous_dialogue.append(dialogues_content)
            except:
                pass
        return previous_dialogue

    # Convert Python-style unicode escapes to actual characters.
    def fix_unicode_escapes(text):
        import re
        try:
            unichr
            def replace_escape(match):
                seq = match.group(1)
                if seq.startswith('u') and len(seq) == 5:
                    try:
                        return unichr(int(seq[1:], 16))
                    except (ValueError, OverflowError):
                        return match.group(0)
                if seq.startswith('U') and len(seq) == 9:
                    try:
                        return unichr(int(seq[1:], 16))
                    except (ValueError, OverflowError):
                        return match.group(0)
                if seq.startswith('x') and len(seq) == 3:
                    try:
                        return unichr(int(seq[1:], 16))
                    except (ValueError, OverflowError):
                        return match.group(0)
                escapes = {
                    'n': '\n',
                    't': '\t',
                    'r': '\r',
                    'f': '\f',
                    'b': '\b',
                    '"': '"',
                    "'": "'",
                    '\\': '\\',
                }
                if seq in escapes:
                    return escapes[seq]
                return match.group(0)
        except NameError:
            def replace_escape(match):
                seq = match.group(1)
                if seq.startswith('u') and len(seq) == 5:
                    try:
                        return chr(int(seq[1:], 16))
                    except (ValueError, OverflowError):
                        return match.group(0)
                if seq.startswith('U') and len(seq) == 9:
                    try:
                        return chr(int(seq[1:], 16))
                    except (ValueError, OverflowError):
                        return match.group(0)
                if seq.startswith('x') and len(seq) == 3:
                    try:
                        return chr(int(seq[1:], 16))
                    except (ValueError, OverflowError):
                        return match.group(0)
                escapes = {
                    'n': '\n',
                    't': '\t',
                    'r': '\r',
                    'f': '\f',
                    'b': '\b',
                    '"': '"',
                    "'": "'",
                    '\\': '\\',
                }
                if seq in escapes:
                    return escapes[seq]
                return match.group(0)
        
        global unicode_escape_fix_pattern
        text = unicode_escape_fix_pattern.sub(replace_escape, text)
        return text

    

    # Translate a batch using Microsoft Edge (Bing) API (requests).
    def _send_batch_translation_request_edge(texts, target_lang):
        import random
        try:
            url = "https://edge.microsoft.com/translate/translatetext?from=&to={0}&isEnterpriseClient=true".format(target_lang)
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Content-Type": "application/json",
                "Priority": "u=1, i",
                "User-Agent": random.choice(USER_AGENTS),
            }
            session = session_manager.get_session()
            response = session.post(
                url,
                headers=headers,
                json=texts,
                proxies=session_manager._current_proxies,
                timeout=20,
            )
            if response.status_code == 200:
                result = response.json()
                result = [item['translations'][0]['text'] for item in result]
                return result
            else:
                print("Edge failed ", response.status_code, response)
        except Exception as e:
            print("Request failed: {}".format(str(e)))
            raise
        return texts

    # Translate a batch using Microsoft Edge (Bing) API (urllib2).
    def _send_batch_translation_request_edge_urllib2(texts, target_lang):
        import json
        import random
        import urllib2
        try:
            url = "https://edge.microsoft.com/translate/translatetext?from=&to={0}&isEnterpriseClient=true".format(target_lang)
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Content-Type": "application/json",
                "Priority": "u=1, i",
                "User-Agent": random.choice(USER_AGENTS),
            }
            request_data = texts
            req = urllib2.Request(url, json.dumps(request_data), headers)
            global urllib2_opener
            opener = urllib2_opener
            response = opener.open(req, timeout=20)
            response_data = response.read()
            result = json.loads(response_data)
            translated_texts = [item['translations'][0]['text'] for item in result]
            return translated_texts
        except Exception as e:
            print("Edge translation error: {}".format(str(e)))
            return texts

    # Translate a batch using Yandex API (requests).
    def _send_batch_translation_request_yandex(texts, target_lang):
        import random
        import uuid
        try:
            url = "http://translate.yandex.net/api/v1/tr.json/translate"
            headers = {
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "{0},en-US;q=0.9,en;q=0.8".format(target_lang),
                "authority": "browser.translate.yandex.net",
                "priority": "u=1, i",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "user-agent": random.choice(USER_AGENTS)
            }
            uuid_v4 = str(uuid.uuid4())
            yandex_id = "{0}-0-0".format(uuid_v4.replace("-", ""))
            params = {"sid": yandex_id, "srv": "android", "format": "html"}
            data = {"text": texts, "lang": target_lang}
            session = session_manager.get_session()
            response = session.post(
                url,
                headers=headers,
                params=params,
                data=data,
                proxies=session_manager._current_proxies,
                timeout=20
            )
            if response.status_code == 200:
                result = response.json()
                if 'text' in result:
                    result = result['text']
                    if isinstance(result, list):
                        return result
                    return result
            else:
                print("yandex failed ", response.status_code, response.text)
                print("Request URL:", response.url)
        except Exception as e:
            print("Request failed: {}".format(str(e)))
        return texts

    # Translate a batch using Yandex API (urllib2).
    def _send_batch_translation_request_yandex_urllib2(texts, target_lang):
        import json
        import random
        import urllib2
        import uuid
        import urllib
        try:
            url = "http://translate.yandex.net/api/v1/tr.json/translate"
            headers = {
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "{0},en-US;q=0.9,en;q=0.8".format(target_lang),
                "authority": "browser.translate.yandex.net",
                "priority": "u=1, i",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "user-agent": random.choice(USER_AGENTS)
            }
            uuid_v4 = str(uuid.uuid4())
            yandex_id = "{0}-0-0".format(uuid_v4.replace("-", ""))
            params = {"sid": yandex_id, "srv": "android", "format": "html"}
            data = {"text": texts, "lang": target_lang}
            url_with_params = url + '?' + urllib.urlencode(params)
            encoded_data = urllib.urlencode(data, doseq=True)
            req = urllib2.Request(url_with_params, data=encoded_data, headers=headers)
            global urllib2_opener
            opener = urllib2_opener
            response = opener.open(req, timeout=20)
            response_data = response.read()
            result = json.loads(response_data)
            if 'text' in result:
                result_text = result['text']
                if isinstance(result_text, list):
                    return result_text
                return result_text
            else:
                print("yandex failed: unexpected response format")
                print("Request URL:", url_with_params)
                return texts
        except Exception as e:
            print("Request failed: {}".format(str(e)))
            return texts

    # Send a batch to the Google HTML API (unified dispatcher).
    def _send_batch_translation_request(html_content, target_lang):
        if REQUESTS_AVAILABLE:
            return _send_batch_translation_request_requests(html_content, target_lang)
        else:
            return _send_batch_translation_request_urllib2(html_content, target_lang)

    # Thread runner for the accurate translation process.
    def accurate_translation_thread(texts, speakers, history_list):
        try:
            translate_accurate_batch(texts, speakers, history_list, persistent.target_languages["google"])
        except Exception as e:
            print("Accurate translation thread error: {}".format(e))

    # Periodically dispatch pending translations, depending on the selected service.
    def process_pending_translations():
        import random
        if not persistent.enable_translation:
            return
        global LAST_TRANSLATION_TIME
        
        time_interval_random = persistent.time_interval
        current_time = renpy.time.time()
        if (current_time - LAST_TRANSLATION_TIME) < time_interval_random:
            return
        LAST_TRANSLATION_TIME = current_time
        if len(mdata.translation_cache) == 0:
            load_translation_cache()

        if (not mdata.PENDING_TRANSLATIONS) and (not mdata.prescan_texts) and (not mdata.auto_pending_accurate):
            return

        PENDING_TRANSLATIONS_copy = mdata.PENDING_TRANSLATIONS
        mdata.PENDING_TRANSLATIONS = {}

        # Accurate mode branch (full text polishing)
        if persistent.accurate_translation_mode:
            global len_accurate_items
            current_size = len(mdata.translation_cache)
            if not hasattr(mdata, '_last_check_time'):
                mdata._last_check_time = renpy.time.time()
                mdata._last_check_size = current_size
            if len_accurate_items is not None:
                if current_size >= len_accurate_items * 0.5:
                    if renpy.time.time() - mdata._last_check_time >= 120:
                        print("========================================")
                        print("Accurate Translation Progress ({}/{})".format(current_size, len_accurate_items))
                        if current_size - mdata._last_check_size < 100:
                            print("Accurate_translation_mode has finished. No more than 100 texts translated in 120 seconds.")
                            print("========================================")
                            renpy.quit()
                            return
                        else:
                            mdata._last_check_time = renpy.time.time()
                            mdata._last_check_size = current_size
                if hasattr(mdata, 'accurate_pending_items') and mdata.accurate_pending_items:
                    texts_to_translate, speakers, history_list = get_accurate_texts_to_translate(PENDING_TRANSLATIONS_copy)
                    if texts_to_translate:
                        renpy.invoke_in_thread(accurate_translation_thread, texts_to_translate, speakers, history_list)
                return

        # Auto mode: first round uses Google/Bing/Yandex in rotation, then enqueue for later refinement.
        if persistent.translation_service == "auto":
            global auto_service_index
            translation_service0 = methods[auto_service_index]
            auto_service_index = (auto_service_index + 1) % 3
            texts_to_translate = get_texts_to_translate(PENDING_TRANSLATIONS_copy, translation_service0)
            if len(texts_to_translate) == 0:
                # Even if no new texts, we may still have queued items for accurate refinement.
                pass
            else:
                renpy.invoke_in_thread(translation_thread, texts_to_translate, translation_service0)

            # Perform accurate re-translation on the queued auto items at a fixed interval.
            if mdata.auto_pending_accurate:
                last_accurate = getattr(mdata, 'last_auto_accurate_time', 0)
                if current_time - last_accurate >= persistent.auto_accurate_interval:
                    # Take a batch of items from the queue.
                    auto_pending_accurate_items=mdata.auto_pending_accurate
                    items = list(auto_pending_accurate_items.items())
                    # We'll process up to persistent.normal_maxtexts items at once.
                    batch = items[:20]
                    rest = items[20:]
                    mdata.auto_pending_accurate = dict(rest)
                    if batch:
                        originals = [k for k, v in batch]
                        # Use the freellm service to get better translations.
                        mdata.last_auto_accurate_time = current_time
                        history_texts=get_previous_dialogue()
                        renpy.invoke_in_thread(accurate_translation_thread, originals, [],history_texts)
                        
            return

        # Standard mode: translate using the configured service.
        else:
            if persistent.translation_service=="deepl" and _normalize_deepl_lang(persistent.target_languages["deepl"])=="noway":
                texts_to_translate = deepl_get_texts_to_translate(PENDING_TRANSLATIONS_copy, "deepl")
                if len(texts_to_translate) > 0:
                    renpy.invoke_in_thread(translation_thread, texts_to_translate,"deepl")
                texts_to_translate_google = deepl_get_texts_to_translate(PENDING_TRANSLATIONS_copy, "google")
                if len(texts_to_translate_google) > 0:
                    renpy.invoke_in_thread(translation_thread, texts_to_translate_google,"google")
            else:
                texts_to_translate = get_texts_to_translate(PENDING_TRANSLATIONS_copy, persistent.translation_service)
                if len(texts_to_translate)>0:
                    renpy.invoke_in_thread(translation_thread, texts_to_translate,persistent.translation_service)

    # Store translation results in the cache and mark texts for redrawing.
    def process_translation_results(translations):
        for original, translated in translations.items():
            try:
                translated = html_unescape(translated)
                translated = adjust_translation_spaces(original, translated)
                if original != translated:
                    
                    mdata.translation_cache[original] = translated
                    mdata.translated_set.add(translated)
                    if r'[' in original and r']' in original:
                        mdata.var_set.add(original)
                else:
                    if original not in mdata.retry_texts_set:
                        mdata.retry_texts_set.add(original)
                        mdata.PENDING_TRANSLATIONS[original] = None
                    else:
                        mdata.translation_cache[original] = translated
            except Exception as e:
                print("Error processing translation for '{0}': {1}".format(translated, str(e)))
        global LAST_SAVE_TIME
        current_time = renpy.time.time()
        if (current_time - LAST_SAVE_TIME) < persistent.save_interval:
            return
        LAST_SAVE_TIME = current_time
        cleanup_empty_sets()
        save_translation_cache()

    # Redraw texts whose translations have arrived.
    def process_redrawing_translations():
        if (not persistent.enable_translation) or(not persistent.display_translation):
            return
        global LAST_REDRAW_TIME
        current_time = renpy.time.time()
        if (current_time - LAST_REDRAW_TIME) < persistent.redraw_time:
            return
        keys_to_process = list(mdata.TEXT_OBJECTS_TO_REDRAW.keys())
        for original_dis in keys_to_process:
            try:
                if original_dis in mdata.translation_cache:
                    text_objs = get_text_objects_for_redraw(original_dis)
                    if not text_objs:
                        continue
                    for text_obj in text_objs:
                        if text_obj is None:
                            continue
                        try:
                            text_obj.dirty = True
                            text_obj.locked = False
                            text_obj.kill_layout()
                            renpy.display.render.redraw(text_obj, 0)
                            if persistent.enhanced_display:
                                if persistent.show_comparison:
                                    text_obj.set_text(original_dis + mdata.translation_cache[original_dis], None, None)
                                else:
                                    text_obj.set_text(mdata.translation_cache[original_dis], None, None)
                            remove_text_content_from_redraw(original_dis)
                        except Exception as e:
                            continue
            except Exception as e:
                print("redraw error", e)
            LAST_REDRAW_TIME = current_time

    # Ensure leading/trailing spaces and tag spacing are preserved in the translation.
    def adjust_translation_spaces(original, translated):
        global tag_pattern
        import re
        if not original:
            return translated
        original_leading_spaces = len(original) - len(original.lstrip())
        translated_leading_spaces = len(translated) - len(translated.lstrip())
        original_trailing_spaces = len(original) - len(original.rstrip())
        translated_trailing_spaces = len(translated) - len(translated.rstrip())
        if translated_leading_spaces != original_leading_spaces:
            translated = translated.lstrip()
            if original_leading_spaces > 0:
                translated = ' ' * original_leading_spaces + translated
        if translated_trailing_spaces != original_trailing_spaces:
            translated = translated.rstrip()
            if original_trailing_spaces > 0:
                translated += ' ' * original_trailing_spaces
        original_parts = tag_pattern.split(original)
        translated_parts = tag_pattern.split(translated)
        if len(original_parts) != len(translated_parts):
            return translated
        result_parts = []
        for i in range(len(original_parts)):
            if original_parts[i].startswith('{') and original_parts[i].endswith('}'):
                original_tag = original_parts[i]
                translated_tag = translated_parts[i]
                translated_tag = translated_tag.strip()
                if translated_tag[0] == '{' and translated_tag[-1] == '}':
                    stripped_translated_tag = translated_tag[1:-1].strip()
                    corrected_tag = '{' + stripped_translated_tag + '}'
                else:
                    corrected_tag = translated_parts[i]
                result_parts.append(corrected_tag)
            else:
                result_parts.append(translated_parts[i])
        return ''.join(result_parts)

    # Build the regex patterns used for glossary term replacement.
    def apply_glossary_patterns():
        import re
        global glossary_patterns, glossary_patterns_bing, glossary_set
        glossary_patterns = []
        glossary_patterns_bing = []
        glossary_set = set()
        if sorted_glossary_terms:
            glossary_patterns = [(re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE),r'<meta content="{0}"/>'.format(glossary_dic[term]))for term in sorted_glossary_terms]
            glossary_patterns_bing = [(re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE),glossary_dic[term]) for term in sorted_glossary_terms]
            for term in sorted_glossary_terms:
                glossary_set.add(glossary_dic[term])

    # Apply glossary replacements to a text (Google-style tagging).
    def apply_glossary(text):
        import re
        global glossary_patterns
        if not persistent.glossary_enabled:
            return text
        if not hasattr(store, "glossary_patterns"):
            return text
        for pattern, replacement in glossary_patterns:
            text = pattern.sub(replacement, text)
        return text
    def _is_valid_unicode_codepoint(cp):
        if 0xD800 <= cp <= 0xDFFF:       
            return False
        if 0xFDD0 <= cp <= 0xFDEF:     
            return False
        if cp & 0xFFFE == 0xFFFE:        
            return False
        if cp > 0x10FFFF:               
            return False
        return True
    def _build_test_string(ranges):
        chars = []
        for start, end in ranges:
            for cp in range(start, end + 1):
                if _is_valid_unicode_codepoint(cp):
                    try:
                        chars.append(unichr(cp))   
                    except:
                        chars.append(chr(cp))
        return ''.join(chars)
    # Hook: replace the font of TextSegment with a FontGroup that supports the translation font.
    def hook_tssubseg(self, s):
        if ((not persistent.enable_translation) or (not persistent.display_translation)) and (not persistent.enhanced_display) :
            return original_subsegment(self, s)
        if isinstance(self.font, FontGroup):
            if self.font not in font_groups:
                try:
                    new_fontgroup = FontGroup()
                    new_fontgroup.add(emoji_font, 0x1F300, 0x1FAFF)
                    new_fontgroup.add(main_font, None, None)
                    font_groups[self.font] = new_fontgroup
                    self.font = new_fontgroup
                except Exception as e:
                    print("fontgroup replace error", self.font, e)
            return original_subsegment(self, s)
        try:
            global latest_font
            if latest_font != self.font:
                if self.font not in font_groups:
                    new_fontgroup = FontGroup()

                    if main_font and main_font != self.font:
                        try:
                            new_fontgroup.add(main_font, None, None)
                        except Exception as e:
                            print("Failed to add main font ", main_font, e)
                            font_groups[self.font] = main_font
                            self.font = main_font
                            latest_font = self.font
                            return original_subsegment(self, s)
                    try:
                        for i in range(0x00020, 0x0007F):
                            new_fontgroup.map[i] = self.font
                        if persistent.more_unicode_cover:
                            try:
                                
                                face = renpy.text.font.load_face(self.font, "harfbuzz")
                                face_f = renpy.text.hbfont.HBFont(face, int(10 *10), False, False, False, False, False, False, False, False)
                            except Exception:
                                try:
                                    face = renpy.text.font.load_face(self.font, "freetype")
                                    face_f = renpy.text.ftfont.FTFont(face, int(10 * 10), False, False, 0, False, False, False)
                                except Exception as e:
                                    face = renpy.text.font.load_face(self.font)
                                    face_f = renpy.text.ftfont.FTFont(face, int(10 * 10), False, False, 0, False, False, False)
                            test_str = _build_test_string([(0x0020, 0xFFFF)])
                            try:
                                glyphs = face_f.glyphs(test_str)       
                            except:
                                glyphs = face_f.glyphs(test_str,0)                      
                            seen = set()
                            width_counts = {}
                            for g in glyphs:
                                ch = g.character
                                if ch not in seen:
                                    seen.add(ch)
                                    w = g.width
                                    width_counts[w] = width_counts.get(w, 0) + 1
                            max_count = max(width_counts.values())
                            most_common_widths = [w for w, c in width_counts.items() if c == max_count]
                            missing_width = most_common_widths[0]
                            for g in glyphs:
                                if g.width != missing_width and g.width>0:
                                    new_fontgroup.map[g.character] = self.font
                        print("Added current font:", self.font)
                    except Exception as e:
                        print("Failed to add current font ", self.font, e)
                    try:
                        new_fontgroup.add(emoji_font, 0x1F300, 0x1FAFF)
                    except Exception as e:
                        print("Failed to add emoji font ", emoji_font, e)
                    font_groups[self.font] = new_fontgroup
                    self.font = new_fontgroup
                    latest_font = self.font
                else:
                    self.font = font_groups[self.font]
                    latest_font = self.font
        except Exception as e:
            print("Font processing failed:", e)
            self.font = main_font
        return original_subsegment(self, s)
    def _llm_request_requests(messages, provider):
        import random
        global api_index, max_api_index
        if api_index >= max_api_index:
            api_index = 0
        else:
            api_index += 1
        api_key = persistent.api_keys[api_index] if persistent.api_keys else ""
        base_url = persistent.base_url
        model = persistent.model_name
        headers = {
            "Content-Type": "application/json"
        }
        headers["Authorization"] = "Bearer " + api_key
        data = {
            "model": model,
            "messages": messages,
            "temperature": persistent.temperature
        }
        session = session_manager.get_session()
        response = session.post(
            url=base_url,
            headers=headers,
            json=data,
            proxies=session_manager._current_proxies,
            timeout=persistent.timeout
        )
        return response.json()

    def _llm_request_urllib2(messages, provider):
        import json, urllib2, random
        global api_index, max_api_index
        if api_index >= max_api_index:
            api_index = 0
        else:
            api_index += 1
        api_key = persistent.api_keys[api_index] if persistent.api_keys else ""
        base_url = persistent.base_url
        model = persistent.model_name
        headers = {
            "Content-Type": "application/json"
        }
        url = base_url
        headers["Authorization"] = "Bearer " + api_key
        data = {
            "model": model,
            "messages": messages,
            "temperature": persistent.temperature
        }
        global urllib2_opener
        req = urllib2.Request(url, json.dumps(data), headers)
        opener = urllib2_opener
        response = opener.open(req, timeout=persistent.timeout)
        return json.loads(response.read())
    

    # Parse the LLM JSON response and extract the translated HTML.
    def _parse_llm_response(response_data, original_texts):
        try:
            translated_html = response_data['choices'][0]['message']['content'].strip()
            translated_texts = comhtml_to_text(translated_html, original_texts)
            return translated_texts
        except Exception as e:
            print("LLM response parsing error: {}".format(e))
            return original_texts

    # Main translation dispatcher.
    def translate_batch(texts, target_lang, translation_service=persistent.translation_service):
        if (not persistent.enable_translation) or (not texts):
            print("Translation disabled or no texts provided.")
            return texts
        else:
            if translation_service == "LLM" or translation_service == "freellm":
                try:
                    translate_accurate_batch(texts, [], [], target_lang)
                except Exception as e:
                    print("Accurate batch failed,  {}".format(e))
                return {}  
            if translation_service == "bing":
                combined_html, protected_contents, original_texts = text_to_comhtml_edge(texts)
                if REQUESTS_AVAILABLE:
                    translated_html = _send_batch_translation_request_edge(combined_html, target_lang)
                else:
                    translated_html = _send_batch_translation_request_edge_urllib2(combined_html, target_lang)
                if translated_html == combined_html:
                    return texts
                translated_texts = comhtml_to_text_edge(translated_html, original_texts, protected_contents)
                return translated_texts
            if translation_service == "yandex":
                combined_html, protected_contents, original_texts = text_to_comhtml_edge(texts)
                if REQUESTS_AVAILABLE:
                    translated_html = _send_batch_translation_request_yandex(combined_html, target_lang)
                else:
                    translated_html = _send_batch_translation_request_yandex_urllib2(combined_html, target_lang)
                if translated_html == combined_html:
                    return texts
                translated_texts = comhtml_to_text_edge(translated_html, original_texts, protected_contents)
                return translated_texts
            if translation_service == "deepl":
                
                
                if _normalize_deepl_lang(persistent.target_languages["deepl"])=="noway":
                    combined_html, protected_contents, original_texts = text_to_comhtml_edge(texts)
                    if REQUESTS_AVAILABLE:
                        translated_html=_send_batch_translation_request_deepl_texts(combined_html, target_lang)                    
                    else:
                        translated_html=_send_batch_translation_request_deepl_urllib2_texts(combined_html, target_lang)
                    if translated_html == combined_html:
                        return texts
                    translated_texts = comhtml_to_text_edge(translated_html, original_texts, protected_contents)
                else:
                    combined_html,original_texts = text_to_comhtml(texts)
                    if REQUESTS_AVAILABLE:
                        translated_html=_send_batch_translation_request_deepl(combined_html, target_lang)                    
                    else:
                        translated_html=_send_batch_translation_request_deepl_urllib2(combined_html, target_lang)
                    if translated_html==combined_html:
                        return texts
                    translated_texts=comhtml_to_text(translated_html,original_texts)
                return translated_texts
            try:
                combined_html, original_texts = text_to_comhtml(texts)
            except Exception as e:
                print("Error in text to comhtml conversion: {0}".format(str(e)))
                return texts
            try:
                translated_html = _send_batch_translation_request(combined_html, target_lang)
                
                translated_texts = comhtml_to_text(translated_html, original_texts)

                return translated_texts
            except Exception as e:
                print("Batch translation error: {0}".format(str(e)))
                return texts

    # HTML escaping helpers.
    def html_escape(s, quote=True):
        if isinstance(s, bytes):      
            s = s.decode('utf-8')
        s = s.replace("&", "&amp;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        if quote:
            s = s.replace('"', "&quot;")
            s = s.replace('\'', "&#x27;")
            s = s.replace("'", "&#39;")
        return s

    def html_unescape(s, quote=True):
        if isinstance(s, bytes):      
            s = s.decode('utf-8')
        s = s.replace("&amp;", "&")
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        s = s.replace("&quot;", '"')
        s = s.replace("&#x27;", '\'')
        s = s.replace("&#39;", "'")
        return s

    # Encode a list of texts into an HTML snippet for the Google API.
    def text_to_comhtml(texts):
        import re
        global tag_pattern_html 
        protected_texts = []
        original_texts = []
        
        for text_idx, text in enumerate(texts):
            add_text_flag = True
            original_text = text
            text = repr(text)
            if text.startswith("u'") or text.startswith('u"'):
                text = text[1:]
            if text[0] == "u":
                text = text[2:-1]
            else:
                text = text[1:-1]

            def decode_escape(match):
                escape_seq = match.group(0)
                esc_char = escape_seq[1]
                if esc_char == 'u' or esc_char == 'U':
                    hex_str = escape_seq[2:]
                    try:
                        return chr(int(hex_str, 16))
                    except:
                        return escape_seq
                elif esc_char == 'x':
                    hex_str = escape_seq[2:]
                    try:
                        return chr(int(hex_str, 16))
                    except:
                        return escape_seq
                elif '0' <= esc_char <= '7':
                    try:
                        return chr(int(escape_seq[1:], 8))
                    except:
                        return escape_seq
                else:
                    return escape_seq

            text = escaped_char_pattern.sub(decode_escape, text)

            def replace_escape(match):
                char = match.group(1)
                if char in ['\\', '"', "'", ' ', '%', '&', 'u', 'U', 'x', 'X']:
                    return match.group(0)
                return '<link rel="\\{0}"/>'.format(char)

            text = html_escape(text)
            text = _unified_pattern.sub(_unified_replace, text)

            stripped_text = text.strip()
            if stripped_text.startswith('<') and stripped_text.endswith('>'):
                tags = tag_pattern_html.findall(stripped_text)
                if len(tags) == 1 and tags[0] == stripped_text:
                    add_text_flag = False
                    continue

            if persistent.glossary_enabled:
                text = apply_glossary(text)

            if add_text_flag:
                def _merge_punct_into_meta(m):
                    tag = m.group(1)
                    punct = m.group(2)
                    last_quote = tag.rfind('"')
                    if last_quote != -1:
                        return tag[:last_quote] + punct + tag[last_quote:]
                    return tag + punct

                global meta_punct_pattern
                text = meta_punct_pattern.sub(_merge_punct_into_meta, text)
                protected_texts.append(text)
                original_texts.append(original_text)

        html_parts = []
        for i, text in enumerate(protected_texts):
            html_parts.append('<div id="{0}">{1}</div>'.format(i, text))
        combined_html = ''.join(html_parts)
        return combined_html, original_texts

    # Decode the HTML response from Google back into a dict of translations.
    def comhtml_to_text(translated_html, texts):
        import codecs
        import re
        from collections import defaultdict
        global comhtml_to_text_pattern
        try:
            translated_texts = {}
            id_to_contents = defaultdict(list)

            for match in comhtml_to_text_pattern.finditer(translated_html):
                idx = int(match.group(1))
                translated_text = match.group(2)
                translated_text = img_pattern.sub(r'\1', translated_text)
                translated_text = source_pattern.sub(r'\1', translated_text)
                translated_text = input_pattern.sub(r'\1', translated_text)
                try:
                    translated_text = link_pattern.sub(lambda match: codecs.decode(match.group(1), 'unicode_escape'),translated_text)
                except Exception as e:
                    print("Error processing match: {0}".format(str(e)))
                    translated_text = link_pattern.sub(r'\1', translated_text)
                translated_text = html_unescape(translated_text)
                id_to_contents[idx].append(translated_text)

            for idx, contents in id_to_contents.items():
                if idx < len(texts):
                    combined_content = ' '.join(contents)
                    translated_texts[texts[idx]] = combined_content
            return translated_texts
        except Exception as e:
            return texts

    # Encode texts for the Edge/Yandex API (different protection method).
    def text_to_comhtml_edge(texts):
        import re
        protected_texts = []
        protected_contents = []
        original_texts = []
        global tag_pattern_html
        
        for text_idx, text in enumerate(texts):
            original_text = text
            text = repr(text)
            if text[0] == "u":
                text = text[2:-1]
            else:
                text = text[1:-1]

            def decode_escape(match):
                escape_seq = match.group(0)
                esc_char = escape_seq[1]
                if esc_char == 'u' or esc_char == 'U':
                    hex_str = escape_seq[2:]
                    try:
                        return chr(int(hex_str, 16))
                    except:
                        return escape_seq
                elif esc_char == 'x':
                    hex_str = escape_seq[2:]
                    try:
                        return chr(int(hex_str, 16))
                    except:
                        return escape_seq
                elif '0' <= esc_char <= '7':
                    try:
                        return chr(int(escape_seq[1:], 8))
                    except:
                        return escape_seq
                else:
                    return escape_seq

            text = escaped_char_pattern.sub(decode_escape, text)

            def add_protected_content(match):
                content = match.group(1)
                index = len(protected_contents)
                protected_contents.append(content)
                return "<b{0}>".format(index)

            def add_protected_content2(match):
                content = match.group(1)
                if content in ['\\', '"', "'", ' ', '%', '&', 'u', 'U', 'x', 'X']:
                    return match.group(0)
                index = len(protected_contents)
                content = "\\" + content
                protected_contents.append(content)
                return "<b{0}>".format(index)

            def glossary_bing_replace(text):
                try:
                    for pattern, replacement in glossary_patterns_bing:
                        index = len(protected_contents)
                        replacement2 = "<b{0}>".format(index)
                        result_text = pattern.sub(replacement2, text)
                        if result_text != text:
                            protected_contents.append(replacement)
                        text = result_text
                except:
                    return text
                return result_text

            text = html_escape(text)
            text = escape_pattern.sub(add_protected_content2, text)
            text = percent_pattern.sub(add_protected_content, text)
            text = brace_pattern.sub(add_protected_content, text)
            text = bracket_pattern.sub(add_protected_content, text)

            stripped_text = text.strip()
            if stripped_text.startswith('<') and stripped_text.endswith('>'):
                tags = tag_pattern_html.findall(stripped_text)
                if len(tags) == 1 and tags[0] == stripped_text:
                    continue

            if persistent.glossary_enabled:
                text = glossary_bing_replace(text)

            protected_texts.append(text)
            original_texts.append(original_text)
        return protected_texts, protected_contents, original_texts

    # Decode the Edge/Yandex response back into a translation dict.
    def comhtml_to_text_edge(translated_html, texts, protected_contents):
        import re
        from collections import defaultdict
        import codecs
        try:
            translated_texts = {}
            id_to_contents = defaultdict(list)

            for idx, trans_text in enumerate(translated_html):
                translated_text = trans_text

                def restore_protected_content(match):
                    index_match = re.search(r'<b(\d+)>', match.group(0))
                    if index_match:
                        index = int(index_match.group(1))
                        if index < len(protected_contents):
                            if persistent.glossary_enabled:
                                try:
                                    if protected_contents[index] in glossary_set:
                                        return protected_contents[index]
                                except:
                                    pass
                            return codecs.decode(protected_contents[index], 'unicode_escape')
                    return match.group(0)

                translated_text = re.sub(r'<b\d+>', restore_protected_content, translated_text)
                translated_text = html_unescape(translated_text)
                id_to_contents[idx].append(translated_text)

            for idx, contents in id_to_contents.items():
                if idx < len(texts):
                    combined_content = ' '.join(contents)
                    translated_texts[texts[idx]] = combined_content
            return translated_texts
        except Exception as e:
            return texts

    # Save translation cache when the game quits.
    def quit_save_translation_cache():
        import json
        if persistent.enable_translation and len(mdata.translation_cache) > persistent.last_saved_cache_size:
            try:
                try:
                    with open(TRANSLATION_CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(mdata.translation_cache, f, ensure_ascii=False, indent=2)
                    print("translation cache saved")
                except:
                    import codecs
                    with codecs.open(TRANSLATION_CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(mdata.translation_cache, f, ensure_ascii=False, indent=2)
            except:
                pass

    # Hook into the text layout system to intercept text and queue for translation.
    def hook_segment_trans(self, tokens, style, renders, text_displayable):
        try:
            if (not persistent.enable_translation) or (not persistent.display_translation):
                return original_cts(self, tokens, style, renders, text_displayable)

            if hasattr(text_displayable, "text") and text_displayable.text:
                text_content = text_displayable.text[0]
                if len(text_content) < 2:
                    return original_cts(self, tokens, style, renders, text_displayable)
                if isinstance(text_content, renpy.display.core.Displayable):
                    if (text_content not in mdata.translation_cache) and (text_content not in mdata.retry_texts_set) and (text_content not in mdata.PRESCAN_TEXTS) and (text_content not in mdata.translated_set) and len(text_content) > 1:
                        mdata.PENDING_TRANSLATIONS[text_content] = None
                        add_text_object_to_redraw(text_content, text_displayable)
                        return original_cts(self, tokens, style, renders, text_displayable)
            else:
                return original_cts(self, tokens, style, renders, text_displayable)

            if text_content in mdata.translation_cache:
                try:
                    new_tokens = text_displayable.tokenize([mdata.translation_cache[text_content]])
                except Exception as e:
                    print("Error in tokenize", str(e))
                    add_text_object_to_redraw(text_content, text_displayable)
                    return original_cts(self, tokens, style, renders, text_displayable)
                try:
                    new_tokens = text_displayable.apply_custom_tags(new_tokens)
                except Exception as e:
                    print("Error in apply_custom_tags", str(e))
                    pass
                try:
                    new_tokens = new_get_displayables(text_displayable, new_tokens)
                except Exception as e:
                    print("Error in new_get_displayables", str(e))
                    pass
                try:
                    result_tokens = []
                    text_token_index = 0
                    new_text_tokens = [token for token in new_tokens if token[0] == 1]
                    old_text_tokens = [token for token in tokens if token[0] == 1]
                    if len(new_text_tokens) != len(old_text_tokens):
                        try:
                            if persistent.show_comparison:
                                new_tokens.append((3, " "))
                                new_tokens = new_tokens + tokens
                            return original_cts(self, new_tokens, style, renders, text_displayable)
                        except:
                            pass
                    new_text_token_index = 0
                    for token in tokens:
                        typi, text = token
                        if typi == 1:
                            if new_text_token_index >= len(new_text_tokens):
                                result_tokens.append(token)
                                continue
                            if text == ' ' and new_text_tokens[new_text_token_index][1] != ' ':
                                result_tokens.append(token)
                                text_token_index += 1
                                continue
                            if new_text_token_index < len(new_text_tokens):
                                result_tokens.append(new_text_tokens[new_text_token_index])
                                new_text_token_index += 1
                                text_token_index += 1
                        else:
                            result_tokens.append(token)
                    if len(result_tokens) < len(new_tokens):
                        remaining_tokens = new_tokens[len(result_tokens) - len(new_tokens):]
                        for token in remaining_tokens:
                            result_tokens.append(token)
                            print("appending extra new tokens", token)
                    if persistent.show_comparison:
                        result_tokens.append((3, " "))
                        result_tokens = result_tokens + tokens
                    return original_cts(self, result_tokens, style, renders, text_displayable)
                except Exception as e:
                    print("Error in token replacement", str(e))
                    print("new_tokens:", new_tokens)
                    print("original tokens:", tokens)
            else:
                if (text_content not in mdata.translation_cache) and (text_content not in mdata.retry_texts_set) and (text_content not in mdata.PRESCAN_TEXTS) and (text_content not in mdata.translated_set) and len(text_content) > 1:
                    mdata.PENDING_TRANSLATIONS[text_content] = None
                    add_text_object_to_redraw(text_content, text_displayable)
                    return original_cts(self, tokens, style, renders, text_displayable)
        except Exception as e:
            print("Error in hook_segment", str(e))
        return original_cts(self, tokens, style, renders, text_displayable)

    # Hook for self-voicing to speak the translated text.
    def tts_trans(self):
        if not (persistent.enable_translation and persistent.display_translation):
            return original_tts(self)
        trans_texts = []
        for i in self.text:
            if i in mdata.translation_cache:
                if isinstance(i, str) or isinstance(i, basestring):
                    if i == r"Self-voicing enabled. Press 'v' to disable.":
                        return original_tts(self)
                trans_texts.append(mdata.translation_cache[i])
            else:
                trans_texts.append(i)
        Text_tmp = Text(trans_texts, self.style)
        return original_tts(Text_tmp)

    # Re-build displayable tokens with the correct embedded images.
    def new_get_displayables(text_displayable, tokens):
        try:
            displayables = text_displayable.displayables
            new_tokens = []
            for t in tokens:
                kind, text = t
                if kind == 4:
                    new_tokens.append(t)
                    continue
                if kind == 2:
                    tag, _, value = text.partition("=")
                    if tag == "image" and value:
                        d = renpy.easy.displayable(value)
                        displayables.add(d)
                        new_tokens.append((4, d))
                        continue
                new_tokens.append(t)
        except Exception as e:
            print("Error in new_get_displayables", str(e))
            return tokens
        return new_tokens

    # Session manager for HTTP connections.
    class SessionManager:
        def __init__(self):
            self._session = None
            self._session_urllib2 = None
            self._last_proxy_change = 0
            self._current_proxies = None

        def get_session(self):
            import functools
            if REQUESTS_AVAILABLE:
                import requests
                if self._session is None:
                    self._session = requests.Session()
                    adapter = requests.adapters.HTTPAdapter(
                        pool_connections=100,
                        pool_maxsize=100,
                        max_retries=3,
                        pool_block=False
                    )
                    self._session.mount('http://', adapter)
                    self._session.mount('https://', adapter)
                    self._session.request = functools.partial(
                        self._session.request,
                        timeout=(3.05, 30)
                    )
                return self._session
            return None

        def update_proxies(self):
            current_proxies = get_proxies()
            if current_proxies != self._current_proxies:
                if self._session:
                    self._session.proxies.update(current_proxies or {})
                self._current_proxies = current_proxies
                self._last_proxy_change = renpy.time.time()

        def close(self):
            if self._session:
                self._session.close()
                self._session = None
            self._session_urllib2 = None

    def cleanup_sessions():
        session_manager.close()

    # Toggle translation on/off.
    def toggle_translation():
        try:
            persistent.display_translation = not persistent.display_translation
            renpy.save_persistent()
            mdata.translation_cache = {}
            if persistent.display_translation:
                load_translation_cache()
            else:
                save_translation_cache()
            renpy.call_in_new_context("_force_redraw")
            renpy.restart_interaction()
            renpy.hide_screen("pep_hidden_marker")
            renpy.show_screen("pep_hidden_marker")
            return
        except:
            return

    # Substitute variables inside cached translations periodically.
    def process_variables_translations():
        global LAST_VAR_TIME
        current_time = renpy.time.time()
        if (current_time - LAST_VAR_TIME) < 30:
            return
        for cache_text in list(mdata.var_set):
            try:
                i, did_sub = renpy.substitutions.substitute(cache_text, None, True)
                mdata.translation_cache[i], did_sub = renpy.substitutions.substitute(mdata.translation_cache[cache_text], None, True)
            except Exception as e:
                pass
        LAST_VAR_TIME = renpy.time.time()
        print(LAST_VAR_TIME - current_time)

    # Hook Text.__init__ to capture any text that appears on screen.
    def hook_text_ini(self, *args, **kwargs):
        try:
            if len(args) >= 2:
                text = args[1]
            else:
                text = kwargs.get('text')

            if text is not None and len(text) > 1:
                if (text not in mdata.translation_cache  and text not in mdata.retry_texts_set  and text not in mdata.PRESCAN_TEXTS and text not in mdata.translated_set):
                    mdata.PENDING_TRANSLATIONS[text] = None
        except:
            pass
        return original_text_ini(self, *args, **kwargs)

    # Perform all module initialization.
    trans_init()
    if persistent.glossary_enabled:
        load_glossary()
    if REQUESTS_AVAILABLE:
        session_manager = SessionManager()
        session_manager.update_proxies()

    # Container for all mod data.
    class ModDataContainer(object):
        pass
    mdata = ModDataContainer()
    DIC_CONSTANTS = ["translation_cache", "font_size_cache", "TEXT_OBJECTS_TO_REDRAW", "PENDING_TRANSLATIONS", "accurate_text_to_idx", "auto_pending_accurate"]
    for var_name in DIC_CONSTANTS:
        if var_name == "auto_pending_accurate":
            setattr(mdata, var_name, {})
        else:
            setattr(mdata, var_name, {})
    
    SET_CONSTANTS = ["retry_texts_set", "PRESCAN_TEXTS", "translated_set", "prescan_texts", "var_set"]
    for var_name in SET_CONSTANTS:
        setattr(mdata, var_name, set())
    LIST_CONSTANTS = ["accurate_pending_items"]
    for var_name in LIST_CONSTANTS:
        setattr(mdata, var_name, [])
    # Initialize the auto accurate queue and timer.
    mdata.auto_pending_accurate = {}
    mdata.last_auto_accurate_time = 0

    # Overwrite core Ren'Py methods.
    original_subsegment = renpy.text.text.TextSegment.subsegment
    renpy.text.text.TextSegment.subsegment = hook_tssubseg
    if persistent.auto_detect_system_language:
        auto_set_language_from_system()
    if persistent.auto_detect_language:
        detect_language_from_text(persistent.language_detection_text)
    if not persistent.cache_only:
        config.periodic_callbacks.append(process_pending_translations)
    load_translation_cache()
    config.periodic_callbacks.append(process_redrawing_translations)
    if persistent.var_apply:
        config.periodic_callbacks.append(process_variables_translations)
    try:
        config.quit_callbacks.append(quit_save_translation_cache)
        if REQUESTS_AVAILABLE:
            config.quit_callbacks.append(cleanup_sessions)
    except:
        print("config.quit_callbacks.append error")
        pass
    original_cts = renpy.text.text.Layout.segment
    renpy.text.text.Layout.segment = hook_segment_trans
    if persistent.enable_rtl:
        renpy.config.rtl = True
    original_tts = renpy.text.text.Text._tts
    renpy.text.text.Text._tts = tts_trans
    original_text_ini = renpy.text.text.Text.__init__
    renpy.text.text.Text.__init__ = hook_text_ini

    if "pep_hidden_marker" not in config.overlay_screens:
        config.overlay_screens.append("pep_hidden_marker")
    if (persistent.PRESCAN_FLAG == 0) and (not persistent.prescan_skip):
        renpy.invoke_in_thread(prerun)
        persistent.PRESCAN_FLAG = 1
        renpy.save_persistent()
    if persistent.dns_cache and (not persistent.proxies_enabled) :
        import socket
        _original_getaddrinfo = socket.getaddrinfo
        _DOMAINS_TO_PREFETCH = [
            "oneshot-free.www.deepl.com",
            "translate-pa.googleapis.com",
            "edge.microsoft.com",
            "translate.yandex.net",      
        ]
        _DNS_CACHE = {}
        for dom in _DOMAINS_TO_PREFETCH:
            v4_list = []
            addrs = []
            try:
                infos = _original_getaddrinfo(dom, 443, 0, socket.SOCK_STREAM, socket.IPPROTO_TCP)
                for fam, typ, pro, cn, addr in infos:
                    ip=addr[0]
                    if fam == socket.AF_INET and ip not in v4_list:
                        v4_list.append(ip)
                if len(v4_list)>0:
                    for ipv4 in v4_list:
                        addrs.append((socket.AF_INET, ipv4))
                else:
                    for fam, typ, pro, cn, addr in infos:
                        addrs.append((fam, addr[0]))
            except Exception:
                pass
            _DNS_CACHE[dom] = addrs  
        print(_DNS_CACHE)
        def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            if host in _DNS_CACHE:
                cached = _DNS_CACHE[host]
                try:
                    port_int = int(port)
                except (TypeError, ValueError):
                    port_int = 0
                results = []
                for fam, ip in cached:
                    if family == 0 or family == fam:
                        results.append((fam, socket.SOCK_STREAM, proto, '', (ip, port_int)))
                if results:
                    return results
            return _original_getaddrinfo(host, port, family, type, proto, flags)
        
        socket.getaddrinfo = _patched_getaddrinfo
init -998 python:
    # Helper to call the freellm API (used by accurate mode).
    def call_freellm_chat(messages, urlindex=None, temperature=None, model_override=None):
        import json
        import random
        import uuid
        import string

        if temperature is None:
            temperature = persistent.temperature
        if urlindex is None or urlindex == "random":
            urlindex = random.randint(0, 1)

        if model_override is None or model_override == "random":
            model = random.choice(persistent.accurate_model_list)
        else:
            model = model_override

        urls = [
            "https://netwrck.com/api/chatpred_or",
            "https://api.deepai.org/hacking_is_a_serious_crime"
        ]
        headers_list = [
            {
                'authority': 'netwrck.com',
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'origin': 'https://netwrck.com',
                'referer': 'https://netwrck.com/',
                'user-agent': random.choice(USER_AGENTS),
                "DNT": "1",
                "Sec-CH-UA": '"Not/A)Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": 'Windows'
            },
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "api-key": "tryit-53926507126-2c8a2543c7b5638ca6b92b6e53ef2d2b",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": random.choice(USER_AGENTS),
                "DNT": "1",
                "Sec-CH-UA": '"Not/A)Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": 'Windows'
            }
        ]
        url = urls[urlindex]
        headers = headers_list[urlindex]

        formatted_prompt = format_prompt(messages, add_special_tokens=True, do_continue=True)
        data_payload = [
            {
                "query": formatted_prompt,
                "examples": [],
                "model_name": model,
                "temperature": temperature,
            },
            {
                "chat_style": "chat",
                "chatHistory": json.dumps(messages),
                "model": model,
                "temperature": temperature,
                "hacker_is_stinky": "very_stinky"
            }
        ]
        data = data_payload[urlindex]
        try:
            if REQUESTS_AVAILABLE:
                session = session_manager.get_session()
                if urlindex in (0, 1):
                    cookies = {"__Host-session": uuid.uuid4().hex, '__cf_bm': uuid.uuid4().hex}
                    session.cookies.update(cookies)
                if urlindex == 0:
                    response = session.post(url, data=json.dumps(data), headers=headers,
                                            proxies=session_manager._current_proxies, timeout=persistent.timeout)
                    response.encoding = 'utf-8'
                    return fix_unicode_escapes(response.text.strip())
                else:
                    response = session.post(url, headers=headers, data=data,
                                            proxies=session_manager._current_proxies, timeout=persistent.timeout)
                    return response.text.strip()
            else:
                import urllib2
                import urllib
                if urlindex == 0:
                    req = urllib2.Request(url, json.dumps(data), headers)
                else:
                    req = urllib2.Request(url, urllib.urlencode(data), headers)
                global urllib2_opener
                response = urllib2_opener.open(req, timeout=persistent.timeout)
                result = response.read()
                if urlindex == 0:
                    return fix_unicode_escapes(result.strip())
                else:
                    try:
                        import gzip
                        import StringIO
                        buffer = StringIO.StringIO(result)
                        f = gzip.GzipFile(fileobj=buffer)
                        result = f.read()
                    except:
                        pass
                    return result.strip()
        except Exception as e:
            print("accu error :", urlindex, model, e)

    def call_LLM_chat(messages, original_texts, target_lang=persistent.target_languages["LLM"]):
        try:
            provider = "openai"
            if REQUESTS_AVAILABLE:
                translated_html = _llm_request_requests(messages, provider)
            else:
                translated_html = _llm_request_urllib2(messages, provider)
            if not translated_html:
                return original_texts
            return translated_html
        except Exception as e:
            print(str(e))
            return original_texts

    

    def translate_accurate_batch(texts, speakers, history_list, target_lang=persistent.target_languages["google"]):
        if not texts:
            return
        try:
            google_translations = []
            originals = texts

            history_text = "\n".join(history_list) if history_list else get_previous_dialogue()
            combined_html, original_texts = text_to_comhtml(texts)
            translated_combined_html = _send_batch_translation_request(combined_html, target_lang)
            speaker_map = {idx: speakers[idx] if idx < len(speakers) else "unknown"  for idx in range(len(original_texts))}

            translated_html = accurate_translate_batch_html(combined_html, translated_combined_html, original_texts,
                                                            speaker_map, target_lang, history_text)
            if persistent.translation_service == "LLM":
                translated_texts = _parse_llm_response(translated_html, original_texts)
            else:
                translated_texts = comhtml_to_text(translated_html, original_texts)

            if not isinstance(translated_texts, dict):
                for text in texts:
                    mdata.PENDING_TRANSLATIONS[text] = None
                return
            diff1 = list(set(texts) - set(translated_texts.keys()))
            if len(diff1) > 0:
                for text in diff1:
                    mdata.PENDING_TRANSLATIONS[text] = None
            if translated_texts != texts and len(texts) == len(list(translated_texts.keys())):
                bad_patterns = ["src=", "meta name=", "rel=", "meta content="]
                for original, translated in translated_texts.items():
                    if any(pattern in translated for pattern in bad_patterns) or (''.join(original.split()).lower() == ''.join(translated.split()).lower()):
                        mdata.PENDING_TRANSLATIONS[original] = None

                process_translation_results(translated_texts)
            else:
                for text in texts:
                    mdata.PENDING_TRANSLATIONS[text] = None
        except Exception as e:
            print("accurate batch error",str(e))
            for text in texts:
                mdata.PENDING_TRANSLATIONS[text] = None
            return

init 999 python:
    _original_say_menu_text_filter = config.say_menu_text_filter

    def translation_chain_filter(text):
        current_text = text
        if (not persistent.enable_translation) or (persistent.PRESCAN_FLAG == 0):
            return current_text
        if _original_say_menu_text_filter is not None:
            try:
                current_text = _original_say_menu_text_filter(text)
            except Exception as e:
                print("Original filter error: {}".format(e))

        if current_text in mdata.translation_cache:
            return current_text
        if (current_text not in mdata.retry_texts_set) and (current_text not in mdata.PRESCAN_TEXTS) and (current_text not in mdata.translated_set):
            mdata.PENDING_TRANSLATIONS[current_text] = None
        return current_text

    config.say_menu_text_filter = translation_chain_filter

init 999 python:
    def screenshot_and_compress(screenshot_path=None):
        import os
        if screenshot_path is None:
            screenshot_path = os.path.join(renpy.config.savedir, "ocr_temp.jpg")
        renpy.screenshot(screenshot_path)
        if not os.path.exists(screenshot_path):
            raise Exception("Screenshot failed")
        return screenshot_path

    def _ocr_space_api_urllib2(image_path, api_key="helloworld", engine=3):
        import urllib
        import urllib2
        import base64
        import json
        with open(image_path, 'rb') as f:
            image_data = f.read()
        b64 = base64.b64encode(image_data)
        b64 = b'data:image/jpeg;base64,' + b64
        params = {
            'OCREngine': engine,
            'isTable': 'true',
            'detectOrientation': 'true',
            'scale': 'true',
            'base64Image': b64
        }
        url = "https://api.ocr.space/parse/image"
        headers = {'apikey': api_key}
        req = urllib2.Request(url, urllib.urlencode(params), headers)
        response = urllib2_opener.open(req, timeout=60)
        return json.loads(response.read())

    def ocr_space_api(image_path, api_key="helloworld", engine=3):
        import json
        url = "https://api.ocr.space/parse/image"
        payload = {
            'apikey': api_key,
            'OCREngine': engine,
            'isTable': 'true',
            'detectOrientation': 'true',
            'scale': 'true',
        }
        try:
            if REQUESTS_AVAILABLE:
                with open(image_path, 'rb') as f:
                    files = {'file': f}
                    session = session_manager.get_session()
                    r = session.post(url, files=files, data=payload,
                                    proxies=session_manager._current_proxies,
                                    timeout=60)
                    resp = r.json()
                    parsed = resp.get('ParsedResults', [])
                    if parsed:
                        return parsed[0].get('ParsedText', '').strip()
                    return resp
            else:
                resp = _ocr_space_api_urllib2(image_path, api_key, engine=3)
                parsed = resp.get('ParsedResults', [])
                if parsed:
                    return parsed[0].get('ParsedText', '').strip()
                return resp
        except Exception as e:
            renpy.notify("OCR request failed: " + str(e))
            return str(e)

    def ocr_invoke(image_path):
        original_text = ocr_space_api(image_path, persistent.ocr_api_key, engine=3)
        if not original_text:
            renpy.notify("OCR failed to get original texts")
            print("OCR failed to get original texts")
            return
        else:
            renpy.notify("OCR results:{0}".format(original_text))
            print("OCR results:", original_text)
        renpy.show_screen("ocr_result_screen", original=original_text)

    def ocr_screenshot_and_translate():
        if not persistent.ocr_enabled:
            return
        temp_path = os.path.join(renpy.config.savedir, "ocr_temp.jpg")
        image_path = screenshot_and_compress(temp_path)
        print(image_path)
        renpy.notify(image_path)
        try:
            renpy.invoke_in_thread(ocr_invoke, image_path)
        except Exception as e:
            renpy.notify("OCR Error: " + str(e))
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass

    config.keymap["ocr_translate"] = ["ctrl_alt_K_o"]
    config.underlay.append(renpy.Keymap(ocr_translate=Function(ocr_screenshot_and_translate)))

screen ocr_result_screen(original):
    modal True
    zorder 2000
    frame:
        background "#000000aa"
        xfill True
        yfill True

        vbox:
            xalign 0.5
            yalign 0.5
            xsize int(0.9 * config.screen_width)
            spacing 20
            hbox:
                xalign 0.5
                label _("{}").format(persistent.translation_service) text_color "#ffffff"
            viewport:
                yinitial 0.0
                scrollbars "vertical"
                mousewheel True
                xfill True
                ymaximum 400
                vbox:
                    text original color "#ffffff"

            null height 10
            hbox:
                xalign 0.5
                textbutton _("Close") action Hide("ocr_result_screen")

screen force_redraw():
    timer .1 action Return()

label _force_redraw:
    call screen force_redraw
    pause .1
    return

screen pep_hidden_marker():
    zorder 999
    vbox:
        xalign persistent.x_button_pos
        yalign persistent.y_button_pos
        spacing 2
        if persistent.show_toggle_button:
            button:
                xalign persistent.x_button_pos
                yalign persistent.y_button_pos
                xpadding 5
                ypadding 5
                text "<<<":
                    if persistent.display_translation:
                        color "#9a9af8"
                    else:
                        color "#f7a0a3ff"
                action Function(toggle_translation)
        if persistent.show_ocr_button and persistent.ocr_enabled:
            button:
                xpadding 5
                ypadding 5
                text "OCR":
                    color "#9a9af8"
                action Function(ocr_screenshot_and_translate)
        if persistent.show_translation_settings_button and renpy.has_screen("translation_settings"):
            button:
                xpadding 5
                ypadding 5
                text "Settings":
                    color "#9a9af8"
                action Show("translation_settings")
