import re
from collections import defaultdict

# parse_input: 
# it takes a string as input
# returns a list of dictionaries, where each dictionary represents a card list.
def parse_input(input_text):
    lists = input_text.strip().split('\n\n')
    card_lists = []
    for lst in lists:
        cards = re.findall(r'(\d+)x(OP\d{2}-\d{3})', lst)
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
        avg = sum(counts) / len(counts)
        averages[card] = (counts, avg)
    
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
    
    for card, (counts, avg) in averages.items():
        counts_str = ', '.join(f"{count}x" for count in counts)
        print(f"{card}: counts = [{counts_str}], average = {avg:.2f} in {len(counts)} lists")

# Entry point of the script
if __name__ == "__main__":
    main()