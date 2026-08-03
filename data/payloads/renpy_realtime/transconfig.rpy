init python:
    config.keymap["translation_settings"] = ["ctrl_alt_K_t"]
    config.underlay.append(renpy.Keymap(translation_settings=Show("translation_settings")))

    def update_cache():
        persistent.enable_translation = not persistent.enable_translation
        persistent.display_translation = persistent.enable_translation
        if persistent.enable_translation:
            load_translation_cache()
        else:
            save_translation_cache()
        renpy.save_persistent()
        return

    glossary_original = ""
    glossary_translation = ""
    glossary_editing = ""

    def save_glossary_entry():
        global glossary_original, glossary_translation
        if glossary_original and glossary_translation:
            if add_glossary_entry(glossary_original.strip(), glossary_translation.strip()):
                glossary_original = ""
                glossary_translation = ""
                renpy.notify(_("Glossary entry added successfully"))
                return 
            else:
                renpy.notify(_("Failed to add glossary entry"))
                return
        else:
            renpy.notify(_("Please enter both original word and translation"))
            return 

    def set_glossary_field(field_type):
        global glossary_editing
        glossary_editing = field_type
        if field_type == "original":
            renpy.call_in_new_context("glossary_input_original")
        elif field_type == "translation":
            renpy.call_in_new_context("glossary_input_translation")

    def get_simple_input(prompt, default="", length=None, allow_empty=False, is_numeric=False):
        result = renpy.call_screen("simple_input",
            prompt=prompt,
            default=default,
            length=length)
        if result is None or result == "":
            return None if not allow_empty else ""
        if is_numeric:
            try:
                if "." in result:
                    return float(result)
                else:
                    return int(result)
            except ValueError:
                renpy.notify(_("Please enter a valid number"))
                return None
        return result


init -999 python:
    if not hasattr(renpy.store, 'my_old_show_screen'):
        renpy.store.my_old_show_screen = renpy.show_screen

    def my_show_screen(_screen_name, *_args, **kwargs):
        if _screen_name == 'preferences':
            _screen_name = 'my_preferences'
        return renpy.store.my_old_show_screen(_screen_name, *_args, **kwargs)

    renpy.show_screen = my_show_screen

screen my_preferences():
    tag menu
    use preferences
    vbox:
        align(0.99, 0.99)
        textbutton _("Translation Settings") action Show("translation_settings")

screen translation_settings():
    tag menu
    modal True
    zorder 200

    add Solid("#1a1a2e")

    style_prefix "translation_style"

    $ is_portrait = renpy.get_physical_size()[0] < renpy.get_physical_size()[1]

    frame:
        background Solid("#16213e")
        padding (30, 30)
        xalign 0.5
        yalign 0.5

        xmaximum 0.9
        ymaximum 0.9
        xfill True
        yfill True

        has vbox
        label _("Translation Settings") style "translation_title"

        viewport:
            id "translation_viewport"
            scrollbars "vertical"
            mousewheel True
            draggable True
            xfill True
            yfill True

            has vbox

            if is_portrait:
                ysize config.screen_height * 0.7

            if is_portrait:
                vbox:
                    spacing 30
                    xfill True

                    vbox:
                        xfill True
                        spacing 10
                        label _("Enable Translation") style "translation_label"
                        textbutton _(persistent.enable_translation and "Enabled" or "Disabled") action Function(update_cache) style "translation_toggle_button"

                    vbox:
                        xfill True
                        spacing 10
                        label _("Target Language") style "translation_label"
                        textbutton persistent.target_languages["google"] or _("Select") action Function(renpy.call_in_new_context, "change_target_language") style "translation_action_button"

                    vbox:
                        xfill True
                        spacing 10
                        label _("Translation Service") style "translation_label"
                        vbox:
                            spacing 5
                            xfill True
                            textbutton "Auto" action [SetField(persistent, "translation_service", "auto"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "Google" action [SetField(persistent, "translation_service", "google"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "LLM" action [SetField(persistent, "translation_service", "LLM"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "Bing" action [SetField(persistent, "translation_service", "bing"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "FreeLLM" action [SetField(persistent, "translation_service", "freellm"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "Yandex" action [SetField(persistent, "translation_service", "yandex"), Function(renpy.save_persistent)] style "translation_service_button"

            else:
                vbox:
                    spacing 40
                    xfill True

                    vbox:
                        xsize 280
                        spacing 10
                        label _("Enable Translation") style "translation_label"
                        textbutton _(persistent.enable_translation and "Enabled" or "Disabled") action Function(update_cache) style "translation_toggle_button"

                    vbox:
                        xsize 280
                        spacing 10
                        label _("Target Language") style "translation_label"
                        textbutton persistent.target_languages["google"] or _("Select") action Function(renpy.call_in_new_context, "change_target_language") style "translation_action_button"

                    vbox:
                        xsize 280
                        spacing 10
                        label _("Translation Service:{0}".format(persistent.translation_service)) style "translation_label"
                        vbox:
                            spacing 5
                            xfill True
                            textbutton "Auto" action [SetField(persistent, "translation_service", "auto"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "Google" action [SetField(persistent, "translation_service", "google"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "LLM" action [SetField(persistent, "translation_service", "LLM"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "Bing" action [SetField(persistent, "translation_service", "bing"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "FreeLLM" action [SetField(persistent, "translation_service", "freellm"), Function(renpy.save_persistent)] style "translation_service_button"
                            textbutton "Yandex" action [SetField(persistent, "translation_service", "yandex"), Function(renpy.save_persistent)] style "translation_service_button"

            if is_portrait:
                vbox:
                    spacing 30
                    xfill True

                    vbox:
                        xfill True
                        spacing 10
                        label _("Show Comparison") style "translation_label"
                        textbutton _(persistent.show_comparison and "Enabled" or "Disabled") action ToggleField(persistent, "show_comparison") style "translation_toggle_button"

                    vbox:
                        xfill True
                        spacing 10
                        label _("RTL Mode") style "translation_label"
                        textbutton _(persistent.enable_rtl and "Enabled" or "Disabled") action ToggleField(persistent, "enable_rtl") style "translation_toggle_button"

                    
            else:
                vbox:
                    spacing 40
                    xfill True

                    vbox:
                        xsize 280
                        spacing 10
                        label _("Show Comparison") style "translation_label"
                        textbutton _(persistent.show_comparison and "Enabled" or "Disabled") action ToggleField(persistent, "show_comparison") style "translation_toggle_button"

                    vbox:
                        xsize 280
                        spacing 10
                        label _("RTL Mode") style "translation_label"
                        textbutton _(persistent.enable_rtl and "Enabled" or "Disabled") action ToggleField(persistent, "enable_rtl") style "translation_toggle_button"

            if persistent.translation_service == "LLM":
                frame:
                    background Solid("#0f3460")
                    padding (15, 15)
                    xfill True

                    has vbox
                    label _("LLM Settings") style "translation_section_label"

                    if is_portrait:
                        vbox:
                            spacing 20
                            xfill True

                            vbox:
                                xfill True
                                spacing 5
                                label _("Max Tokens") style "translation_sub_label"
                                textbutton str(persistent.max_tokens) action Function(renpy.call_in_new_context, "change_max_tokens") style "translation_action_button"

                            vbox:
                                xfill True
                                spacing 5
                                label _("Temperature") style "translation_sub_label"
                                textbutton str(persistent.temperature) action Function(renpy.call_in_new_context, "change_temperature") style "translation_action_button"

                            vbox:
                                xfill True
                                spacing 5
                                label _("Timeout") style "translation_sub_label"
                                textbutton str(persistent.timeout) action Function(renpy.call_in_new_context, "change_timeout") style "translation_action_button"
                    else:
                        vbox:
                            spacing 40
                            xfill True

                            vbox:
                                xsize 180
                                spacing 5
                                label _("Max Tokens") style "translation_sub_label"
                                textbutton str(persistent.max_tokens) action Function(renpy.call_in_new_context, "change_max_tokens") style "translation_action_button"

                            vbox:
                                xsize 180
                                spacing 5
                                label _("Temperature") style "translation_sub_label"
                                textbutton str(persistent.temperature) action Function(renpy.call_in_new_context, "change_temperature") style "translation_action_button"

                            vbox:
                                xsize 180
                                spacing 5
                                label _("Timeout") style "translation_sub_label"
                                textbutton str(persistent.timeout) action Function(renpy.call_in_new_context, "change_timeout") style "translation_action_button"

            frame:
                background Solid("#0f3460")
                padding (15, 15)
                xfill True

                has vbox
                label _("Add Glossary Entry") style "translation_section_label"

                vbox:
                    spacing 5
                    xfill True

                    label _("Original Word") style "translation_sub_label"

                    vbox:
                        spacing 10
                        xfill True

                        frame:
                            background glossary_original and Solid("#4361ee") or Solid("#2d2d4d")
                            padding (10, 8)
                            xfill True

                            if glossary_original:
                                text glossary_original:
                                    color "#ffffff"
                                    size 16
                            else:
                                text _("Click to enter original word"):
                                    color "#888888"
                                    size 16
                                    italic True
                    vbox:
                        spacing 10
                        xfill True
                        textbutton _("Edit"):
                            action Function(set_glossary_field, "original")
                            style "translation_action_button"

                vbox:
                    spacing 5
                    xfill True

                    label _("Translation") style "translation_sub_label"

                    vbox:
                        spacing 10
                        xfill True
                        frame:
                            background glossary_translation and Solid("#4361ee") or Solid("#2d2d4d")
                            padding (10, 8)
                            xfill True

                            if glossary_translation:
                                text glossary_translation:
                                    color "#ffffff"
                                    size 16
                            else:
                                text _("Click to enter translation"):
                                    color "#888888"
                                    size 16
                                    italic True
                    vbox:
                        spacing 10
                        xfill True
                        textbutton _("Edit"):
                            action Function(set_glossary_field, "translation")
                            style "translation_action_button"

                if glossary_original and glossary_translation:
                    textbutton _("Add to Glossary"):
                        action [
                            Function(save_glossary_entry),
                            Return()
                        ]
                        style "translation_primary_button"
                        xalign 0.5
                else:
                    textbutton _("Add to Glossary"):
                        action NullAction()
                        style "translation_secondary_button"
                        xalign 0.5
                        sensitive False

            frame:
                background Solid("#0f3460")
                padding (15, 15)
                xfill True

                has vbox
                label _("Advanced Settings") style "translation_section_label"
                if is_portrait:
                    vbox:
                        spacing 20
                        xfill True

                        vbox:
                            xfill True
                            spacing 5
                            label _("Context Lines") style "translation_sub_label"
                            textbutton str(persistent.appended_lines) action Function(renpy.call_in_new_context, "change_appended_lines") style "translation_action_button"

                        vbox:
                            xfill True
                            spacing 5
                            label _("Use Proxies") style "translation_sub_label"
                            textbutton _(persistent.proxies_enabled and "Enabled" or "Disabled") action ToggleField(persistent, "proxies_enabled") style "translation_toggle_button"

                        vbox:
                            xfill True
                            spacing 5
                            label _("Time Interval") style "translation_sub_label"
                            textbutton str(persistent.time_interval) action Function(renpy.call_in_new_context, "change_time_interval") style "translation_action_button"
                else:
                    vbox:
                        spacing 40
                        xfill True

                        vbox:
                            xsize 180
                            spacing 5
                            label _("Context Lines") style "translation_sub_label"
                            textbutton str(persistent.appended_lines) action Function(renpy.call_in_new_context, "change_appended_lines") style "translation_action_button"

                        vbox:
                            xsize 180
                            spacing 5
                            label _("Use Proxies") style "translation_sub_label"
                            textbutton _(persistent.proxies_enabled and "Enabled" or "Disabled") action ToggleField(persistent, "proxies_enabled") style "translation_toggle_button"

                        vbox:
                            xsize 180
                            spacing 5
                            label _("Time Interval") style "translation_sub_label"
                            textbutton str(persistent.time_interval) action Function(renpy.call_in_new_context, "change_time_interval") style "translation_action_button"

                vbox:
                    xfill True
                    spacing 5
                    label _("Translation Font") style "translation_sub_label"
                    textbutton persistent.trans_font or _("Default Font") action Function(renpy.call_in_new_context, "change_trans_font") style "translation_action_button"
                
                vbox:
                    xfill True
                    label _("Text Size Scaling")

                    null height 10
                    bar value Preference("font size")

                    label _("Line Spacing Scaling")

                    null height 10

                    bar value Preference("font line spacing")

            vbox:
                xalign 0.5
                spacing 20

                textbutton _("Save & Close") action [Function(renpy.save_persistent), Hide("translation_settings"),Return()] style "translation_primary_button"
                textbutton _("Cancel") action [ Hide("translation_settings"),Return()] style "translation_secondary_button"

label change_target_language:
    $ new_value = get_simple_input(_("Enter target language code:"), default=persistent.target_languages["google"] or "", length=5, allow_empty=True)
    if new_value is not None:
        $ persistent.target_languages["google"] = new_value.strip()
        $ persistent.target_languages["bing"] = new_value.strip()
        $ persistent.target_languages["yandex"] = new_value.strip()
        $ persistent.target_languages["LLM"] = new_value.strip()
        $ persistent.target_languages["freellm"] = new_value.strip()
        $ renpy.save_persistent()
    return

label change_max_tokens:
    $ new_value = get_simple_input(_("Enter max tokens:"), default=str(persistent.max_tokens), length=10, is_numeric=True)
    if new_value is not None:
        $ persistent.max_tokens = new_value
        $ renpy.save_persistent()
    return

label change_temperature:
    $ new_value = get_simple_input(_("Enter temperature:"), default=str(persistent.temperature), length=10, is_numeric=True)
    if new_value is not None:
        $ persistent.temperature = new_value
        $ renpy.save_persistent()
    return

label change_timeout:
    $ new_value = get_simple_input(_("Enter timeout:"), default=str(persistent.timeout), length=10, is_numeric=True)
    if new_value is not None:
        $ persistent.timeout = new_value
        $ renpy.save_persistent()
    return

label change_appended_lines:
    $ new_value = get_simple_input(_("Enter appended lines:"), default=str(persistent.appended_lines), length=5, is_numeric=True)
    if new_value is not None:
        $ persistent.appended_lines = new_value
        $ renpy.save_persistent()
    return

label change_time_interval:
    $ new_value = get_simple_input(_("Enter time interval:"), default=str(persistent.time_interval), length=5, is_numeric=True)
    if new_value is not None:
        $ persistent.time_interval = new_value
        $ renpy.save_persistent()
    return

label change_trans_font:
    $ new_value = get_simple_input(_("Enter translation font:"), default=persistent.trans_font or "", length=50, allow_empty=True)
    if new_value is not None:
        $ persistent.trans_font = new_value.strip()
        $ renpy.save_persistent()
    return

label glossary_input_original:
    $ result = get_simple_input(_("Enter original word:"), default=glossary_original, length=100, allow_empty=True)
    if result is not None:
        $ glossary_original = result
    return

label glossary_input_translation:
    $ result = get_simple_input(_("Enter translation:"), default=glossary_translation, length=100, allow_empty=True)
    if result is not None:
        $ glossary_translation = result
    return

screen simple_input(prompt, default="", length=None):
    modal True
    zorder 200

    default input_value = default

    frame:
        style_prefix "translation_style"
        background Solid("#16213e")
        padding (30, 30)
        xalign 0.5
        yalign 0.5

        vbox:
            spacing 20
            xsize 400

            text prompt:
                color "#ffffff"
                size 26

            input:
                value ScreenVariableInputValue("input_value")
                length length
                color "#ffffff"
                size 22

            vbox:
                xalign 0.5
                spacing 30

                textbutton _("OK"):
                    action Return(input_value)
                    style "translation_primary_button"

                textbutton _("Cancel"):
                    action Return(default)
                    style "translation_secondary_button"

init -1:
    style translation_frame:
        background Solid("#16213e")
        padding (30, 30)

    style translation_title is gui_label:
        color "#ffffff"
        size 30
        bold True
        xalign 0.5

    style translation_label is gui_label:
        color "#e6e6e6"
        size 22
        bold True

    style translation_section_label is translation_label:
        color "#4cc9f0"
        size 20

    style translation_sub_label is gui_label:
        color "#b8b8b8"
        size 18

    style translation_toggle_button is button:
        background Solid("#7209b7")
        hover_background Solid("#4361ee")
        padding (20, 10)

    style translation_toggle_button_text is button_text:
        color "#ffffff"
        size 26

    style translation_action_button is button:
        background Solid("#3a0ca3")
        hover_background Solid("#4361ee")
        padding (20, 10)

    style translation_action_button_text is button_text:
        color "#ffffff"
        size 26

    style translation_service_button is button:
        background Solid("#7209b7")
        hover_background Solid("#f72585")
        padding (20, 10)

    style translation_service_button_text is button_text:
        color "#ffffff"
        size 26

    style translation_primary_button is button:
        background Solid("#4361ee")
        hover_background Solid("#3a0ca3")
        padding (20, 10)

    style translation_primary_button_text is button_text:
        color "#ffffff"
        size 26

    style translation_secondary_button is button:
        background Solid("#7209b7")
        hover_background Solid("#f72585")
        padding (20, 10)

    style translation_secondary_button_text is button_text:
        color "#ffffff"
        size 26