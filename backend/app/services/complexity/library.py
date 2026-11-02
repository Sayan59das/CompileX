"""What library calls cost, by name (lower-cased, without module or class prefixes), for all five languages.

Costs that depend on the receiver (a membership test is O(n) on a list but O(1) on a set) are decided in the engine from
the receiver's kind; the sets here only say which family a call belongs to.
"""

# the call adds elements to its receiver
GROW = {
    "append", "add", "push", "push_back", "emplace_back", "emplace", "put", "offer", "addlast", "addfirst", "appendleft",
    "heappush", "enqueue", "push_front", "emplace_front", "insert", "putifabsent", "computeifabsent", "merge", "setdefault",
    "add_edge", "pushleft", "offerlast", "offerfirst", "unshift",
}

# the call removes elements from its receiver (what a `while queue:` loop does to make progress)
SHRINK = {
    "pop", "popleft", "pop_back", "pop_front", "poll", "remove", "removefirst", "removelast", "pollfirst", "polllast",
    "heappop", "dequeue", "shift", "erase", "popitem", "pollfirst", "polllast", "removeat", "remove_if", "heappushpop",
    "heapreplace",
}

# O(1) on any receiver
CONSTANT = {
    "len", "size", "length", "empty", "isempty", "top", "front", "back", "peek", "peekfirst", "peeklast", "getfirst",
    "getlast", "first", "last", "begin", "end", "rbegin", "rend", "cbegin", "cend", "charat", "at", "get", "getordefault",
    "containskey", "has", "abs", "fabs", "min2", "max2", "sqrt", "cbrt", "floor", "ceil", "round", "trunc", "exp", "pow",
    "log", "log2", "log10", "sin", "cos", "tan", "atan", "atan2", "ord", "chr", "int", "float", "bool", "double", "long",
    "intvalue", "longvalue", "isdigit", "isalpha", "isalnum", "isupper", "islower", "isspace", "isletter", "tolowercase",
    "touppercase", "swap", "print", "println", "printf", "puts", "scanf", "cin", "cout", "input", "readline", "read",
    "hash", "id", "type", "isinstance", "callable", "numeric_limits", "signum", "hypot", "gcd2", "bit_count", "popcount",
    "clz", "ctz", "__builtin_popcount", "__builtin_clz", "__builtin_ctz", "setdefault", "random", "randint", "next",
    "iter", "hasnext", "getkey", "getvalue", "valueof", "nanotime", "currenttimemillis", "time", "assert", "min_value",
    "max_value", "isnan", "isinf", "compare", "compareto2", "equalsignorecase2", "tostring1", "emplace1", "reserve",
    "capacity", "shrink_to_fit", "resize1", "ensurecapacity", "trimtosize", "isfull", "contains1", "bit_length",
    "numberoftrailingzeros", "numberofleadingzeros", "bitcount", "highestonebit", "lowestonebit", "fill1", "add1", "set1",
}

# O(size of the receiver)
LINEAR_RECV = {
    "copy", "deepcopy", "reverse", "join", "split", "strip", "lstrip", "rstrip", "trim", "lower", "upper", "replace",
    "replaceall", "startswith", "endswith", "substring", "substr", "slice", "concat", "tostring", "tolist", "tostr",
    "tochararray", "chars", "values", "keys", "items", "entries", "clone", "equals", "compareto", "tolowercase1",
    "capitalize", "title", "swapcase", "zfill", "center", "ljust", "rjust", "expandtabs", "partition", "rpartition",
    "splitlines", "format", "encode", "decode", "isnumeric", "isdecimal", "tuple", "frozenset", "list", "reversed1",
    "stream", "boxed", "mapto", "mapToInt", "flat", "flatten", "fill", "assign", "resize", "any", "all", "sum", "count1",
    "bincount", "cumsum", "tobytes", "sorted1", "unique", "distinct", "toarray", "aslist", "listof", "setof", "copyof",
    "copyofrange", "arraycopy", "memcpy", "memmove", "memset", "memcmp", "strlen", "strcpy", "strncpy", "strcmp",
    "strncmp", "strcat", "strcasecmp", "strdup", "strstr", "strchr", "strrchr", "atoi", "atol", "atoll", "stoi", "stol",
    "stoll", "stod", "to_string", "parseint", "parselong", "parsedouble", "valueof1", "iota", "accumulate", "reduce",
    "foreach", "for_each", "transform", "copy_n", "copy_if", "find_if", "count_if", "all_of", "any_of", "none_of",
    "partial_sum", "adjacent_difference", "is_sorted", "equal", "mismatch", "lexicographical_compare", "inner_product",
    "unique_copy", "rotate", "next_permutation", "prev_permutation", "random_shuffle", "shuffle", "fill_n", "swap_ranges",
    "min_element", "max_element", "minmax_element", "bitset", "to_ulong", "toarray1", "flip", "nonzero", "any1",
}

# O(size of the receiver), and also for membership-style calls that are O(1) on hash containers
MEMBERSHIP = {"contains", "indexof", "lastindexof", "index", "find", "rfind", "count", "includes", "findindex",
              "containsvalue", "remove", "erase", "lower_bound1", "search", "find_first_of", "binary_search1"}

# O(size of the argument), added to the receiver
LINEAR_ARG = {"extend", "addall", "update", "union", "intersection", "difference", "putall", "removeall", "retainall",
              "containsall", "insertall", "append_range", "merge_sorted", "difference_update", "intersection_update",
              "symmetric_difference", "issubset", "issuperset", "isdisjoint"}

# sorting: O(n log n) in the size of the thing sorted
SORTS = {"sort", "sorted", "stable_sort", "qsort", "partial_sort", "nth_element1", "sortedlist", "sort_values", "argsort",
         "sorteddict", "sortby", "sorted_by", "tosorted"}

# O(log n) on a heap or balanced tree, or a binary search
LOGARITHMIC = {"heappush", "heappop", "heapreplace", "heappushpop", "bisect", "bisect_left", "bisect_right", "insort",
               "insort_left", "insort_right", "lower_bound", "upper_bound", "binary_search", "equal_range", "floorkey",
               "ceilingkey", "floorentry", "ceilingentry", "lowerkey", "higherkey", "firstkey", "lastkey", "headmap",
               "tailmap", "floor1", "ceiling", "higher", "lower", "pollfirstentry", "polllastentry", "binarysearch"}

# O(n) heap construction
HEAPIFY = {"heapify", "make_heap", "build_heap"}

# callbacks run once per element of the receiver (or of the iterable argument)
CALLBACK_EACH = {"map", "filter", "foreach", "for_each", "some", "every", "find", "findindex", "findlast", "reduce",
                 "flatmap", "mapto", "removeif", "anymatch", "allmatch", "nonematch", "count_if", "transform", "find_if",
                 "all_of", "any_of", "none_of", "replaceall", "computeall", "peek1", "takewhile", "dropwhile", "groupby"}

# constructors / builtin conversions that give a collection of a kind
COLLECTION_KIND = {
    "list": "list", "arraylist": "list", "vector": "list", "array": "list", "linkedlist": "deque", "tuple": "tuple",
    "set": "set", "frozenset": "set", "hashset": "set", "linkedhashset": "set", "unordered_set": "set", "bitset": "list",
    "dict": "dict", "hashmap": "dict", "linkedhashmap": "dict", "unordered_map": "dict", "defaultdict": "dict",
    "counter": "dict", "map1": "dict", "ordereddict": "dict", "hashtable": "dict", "object": "dict",
    "deque": "deque", "arraydeque": "deque", "queue": "deque", "stack": "deque", "ordered": "deque", "stringstream": "str",
    "priority_queue": "heap", "priorityqueue": "heap", "minheap": "heap", "maxheap": "heap",
    "treemap": "omap", "map": "omap", "multimap": "omap", "treeset": "oset", "multiset": "oset", "sortedlist": "oset",
    "string": "str", "stringbuilder": "str", "stringbuffer": "str", "str": "str", "bytes": "str", "bytearray": "str",
    "unordered_multiset": "set", "unordered_multimap": "dict", "pair": "tuple", "tuple1": "tuple",
}

# names that are not user functions even if a parameter happens to be called the same
MODULE_NAMES = {"math", "heapq", "bisect", "itertools", "collections", "functools", "sys", "random", "arrays", "collections",
                "integer", "long", "double", "character", "string", "stringbuilder", "list", "map", "set", "objects", "std",
                "math2", "json", "console", "number", "object", "array", "boolean", "system", "thread", "executors"}
