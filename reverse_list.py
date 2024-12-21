import re

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.readlines()
            matches = []

            for line in content:
                code = line.split(" ")[0]
                match = re.findall(r"\[(.*?)\]", line)[0].split(", ")
                ncols = len(match)
                matches.append((code, match))

            for i in range(0, ncols):
                list = "1xOP07-079\n"
                for c, m in matches:
                    if m[i][0] != "0":
                        list += f"{m[i]}{c}\n"
                print(f"{list}")

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    file_path = 'output/Black_Rob_Lucci_21122024_011533.txt'
    read_file(file_path)