import sys

from generate import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--condition", "I"] + sys.argv[1:]
    main()
