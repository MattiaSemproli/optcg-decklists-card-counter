import re
from collections import defaultdict
from opcardlist import get_card
import tkinter as tk
from datetime import datetime
import numpy as np
from collections import Counter

# display_output:
# it takes output text, leader name and colors as input
def display_output(output_text, leader, colors):
    root = tk.Tk()
    if len(colors) == 1:
        root.title(f"Decklist Information: {colors[0]} {leader}")
    else:
        root.title(f"Decklist Information: {colors[0]} & {colors[1]} {leader}")

    # Insert a blank line at the start for padding
    output_text = "\n" + output_text

    # Set default font
    default_font = ("Consolas", 10)

    # Create a Label widget for non-selectable text
    label = tk.Label(
        root,
        text=output_text,
        font=default_font,
        bg="white",
        justify="center",
        anchor="center"
    )
    label.pack(fill=tk.BOTH, expand=True)

    # Calculate dimensions based on content
    lines = output_text.split('\n')
    max_line_length = max(len(line) for line in lines)
    num_lines = len(lines)
    char_width = 8  # Approximate width of a character in pixels
    char_height = 18  # Approximate height of a line in pixels
    window_width = char_width * max_line_length
    window_height = char_height * num_lines

    # Center the window on the screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    position_top = int(screen_height / 2 - window_height / 2)
    position_right = int(screen_width / 2 - window_width / 2)
    root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

    # Make the window non-resizable
    root.resizable(False, False)

    # Bring the window to the front and activate it
    root.attributes("-topmost", True)
    root.update()
    root.focus_force()
    root.attributes("-topmost", False)

    root.mainloop()

# parse_input: 
# it takes a string as input
# returns a list of dictionaries, where each dictionary represents a card list.
def parse_input(input_text):
    lists = input_text.strip().split('\n\n')
    card_lists = []
    for lst in lists:
        cards = re.findall(r'(\d+)x(OP\d{2}-\d{3})', lst)
        cards.extend(patt for patt in re.findall(r'(\d+)x(P-\d{3})', lst))
        cards.extend(patt for patt in re.findall(r'(\d+)x(ST\d{2}-\d{3})', lst))
        cards.extend(patt for patt in re.findall(r'(\d+)x(EB\d{2}-\d{3})', lst))
        card_lists.append({card: int(count) for count, card in cards})

    card_lists = normalize_card_lists(card_lists)

    return card_lists

# normalize_card_lists: 
# it takes a list of dictionaries as input
# returns a list of dictionaries, where each dictionary represents a card list with the same keys.
def normalize_card_lists(card_lists):
    all_cards = set()
    for card_list in card_lists:
        all_cards.update(card_list.keys())
    
    normalized_lists = []
    for card_list in card_lists:
        normalized_list = {card: card_list.get(card, 0) for card in all_cards}
        normalized_lists.append(normalized_list)
    
    return normalized_lists

# calculate_averages: 
# it takes a list of dictionaries as input
# returns a dictionary where each key is a card and each value is a tuple containing a list of counts and the average count.
def calculate_averages(card_lists):
    card_counts = defaultdict(list)
    for card_list in card_lists:
        for card, count in card_list.items():
            card_counts[card].append(count)
    
    averages = {}
    for card, counts in card_counts.items():
        averages[card] = (counts, (np.count_nonzero(counts), Counter(counts)))
    return averages

# main:
def main():
    print("Enter the card lists (separate lists with a blank line, end input with two blank lines):")
    input_text = ""
    blank_line_count = 0
    while True:
        try:
            line = input()
            if line.strip() == "":
                blank_line_count += 1
                if blank_line_count == 2:
                    break
            else:
                blank_line_count = 0
            input_text += line + "\n"
        except EOFError:
            break

    card_lists = parse_input(input_text)
    averages = calculate_averages(card_lists)

    output_text = ""
    leader = ""
    colors = ""
    for card, (counts, (played, avg)) in averages.items():
        counts_str = ', '.join(f"{count}x" for count in counts)
        card_info = get_card(card)
        c_name = card_info['Card Name']
        c_cost = f"C{card_info["Cost"]["Generic"]}"
        c_power = f"P{card_info["Power"]}"
        c_category = card_info["Category"]

        c_info = f"{c_name}, {c_cost}, {c_power if c_category != "Event" else c_category}"

        played_list = f"played in {played}/{len(counts)} lists"
        occurrences = f"1x {avg[1]}/{played}, 2x {avg[2]}/{played}, 3x {avg[3]}/{played}, 4x {avg[4]}/{played}"

        # print(f"{card} ({c_name}, {c_cost}, {c_power}) : counts = [{counts_str}], average = {avg:.2f} in {len(counts)} lists")
        if (c_category != "Leader"):
            output_text += f"{card} ({c_info}) : counts = [{counts_str}], {played_list} ({occurrences})\n"

        if (c_category == "Leader"):
            leader = c_name
            colors = card_info["Color"]

    display_output(output_text, leader, colors)

    # dd/mm/YY H:M:S
    dt_string = datetime.now().strftime("%d%m%Y_%H%M%S")
    filename = ""
    if len(colors) == 1:
        filename = f"{colors[0]}_{'_'.join(leader.split(' '))}_{dt_string}.txt"
    else:
        filename = f"{colors[0]}_{colors[1]}_{'_'.join(leader.split(' '))}_{dt_string}.txt"

    if (input("Do you want to save the output to a file? (y/n): ").lower() == "y"):
        print(f"Saving output to {filename}")
        with open(f"output\\{filename}", "x") as file:
            file.write(output_text)
    else:
        print("Output not saved.")

# Entry point of the script
if __name__ == "__main__":
    main()