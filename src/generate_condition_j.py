import sys

from generate import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--condition", "J"] + sys.argv[1:]
    main()
