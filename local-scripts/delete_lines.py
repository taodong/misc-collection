import sys
import argparse


def delete_lines(file_path, start_line, end_line=None):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Convert to 0-based index
    start_idx = start_line - 1
    if end_line is not None:
        end_idx = end_line
    else:
        end_idx = len(lines)

    # Remove lines from start_idx to end_idx (inclusive)
    new_lines = lines[:start_idx] + lines[end_idx:]

    with open(file_path, 'w') as f:
        f.writelines(new_lines)


def main():
    parser = argparse.ArgumentParser(description='Delete lines from a file.')
    parser.add_argument('file', help='File path')
    parser.add_argument('start', type=int, help='Start line number (inclusive, 1-based)')
    parser.add_argument('end', type=int, nargs='?', default=None, help='End line number (inclusive, 1-based, optional)')
    args = parser.parse_args()

    delete_lines(args.file, args.start, args.end)


if __name__ == '__main__':
    main()
