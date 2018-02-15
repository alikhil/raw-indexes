"""
inspired by http://www.di.ufpb.br/lucidio/Btrees.pdf and https://algs4.cs.princeton.edu/62btree/
"""


from typing import TypeVar, Generic, List
from bisect import bisect_right

KeyType = TypeVar('KeyType', int, str)
T = TypeVar('T')

DEGREE = 16   

class SmartKey(Generic[KeyType,T]):

    def __init__(self, key: KeyType, value: T = None) -> None:
        self.key: KeyType = key
        self.value: List[T] = value


    def __str__(self):
        return f"[{self.key}] => {self.value}"

    def __lt__(self, other: 'SmartKey') -> bool:
        return self.key < other.key

    def __eq__(self, other: 'SmartKey') -> bool:
        return self.key == other.key


class Page:
    def __init__(self, bottom: bool) -> None:
        self.bottom = bottom
        self.keys: List[SmartKey] = []
        self.children: List[Page] = []

    def add_key_value(self, key: KeyType, value: T) -> None:

        wrapped_key = SmartKey(key, [value]) # store list of values in bottom nodes
        
        if len(self.keys) == 0:
            self.keys.append(wrapped_key)
        else:
            left_upper_index = bisect_right(self.keys, wrapped_key)
            if (left_upper_index > 0 and self.keys[left_upper_index - 1].key == wrapped_key.key):
                self.keys[left_upper_index - 1].value.extend(wrapped_key.value)
            else: 
                self.keys.insert(left_upper_index, wrapped_key)

    def is_external(self) -> bool:
        return self.bottom

    def find(self, key: SmartKey) -> List[T]:
        """Try to find key in page"""
        left_upper_index = bisect_right(self.keys, key)
        if left_upper_index == 0: 
            if len(self.children) == 0:
                return None
            if (key > self.keys[0]):
                return self.children[1].find(key)
            else:
                return self.children[0].find(key)
        

        prevKey = self.keys[left_upper_index - 1]
        if prevKey.key == key.key:
            return self.keys[left_upper_index - 1].value
        
        if self.is_external():
            # since there is no other way to find key left
            return None
        else:
            if (key > self.keys[left_upper_index - 1]):
                return self.children[left_upper_index ].find(key)
            else:
                return self.children[left_upper_index - 1].find(key)


    def next(self, key: SmartKey) -> 'Page':
        left_upper_index = bisect_right(self.keys, key)
        return self.children[left_upper_index ]


    def is_full(self) -> bool:
        return len(self.keys) == DEGREE * 2 - 1

    def split(self) -> (SmartKey, 'Page'):
        """
            move the highest-ranking half of the keys in the page to a new page
        """
        # should create with same bottom
        r_key = self.keys[DEGREE - 1]
        new_page_keys = self.keys[DEGREE:]     # last half
        self.keys = self.keys[:DEGREE - 1]    # first half
        new_page_children = self.children[DEGREE:]
        self.children = self.children[:DEGREE]

        new_page = Page(self.bottom)
        new_page.keys = new_page_keys
        new_page.children = new_page_children

        return r_key, new_page

    def split_and_add_page(self, ch: 'Page') -> None:
        ind = self.children.index(ch)

        k, z = ch.split()
        self.children.insert(ind + 1, z)
        self.keys.insert(ind, k)

    def find_predecessor(self) -> SmartKey:
        if self.is_external():
            return self.keys[-1]
        return self.children[-1].find_predecessor()

    def find_successor(self) -> SmartKey:
        if self.is_external():
            return self.keys[0]
        return self.children[0].find_successor()

    def merge(self, ind: int, left: 'Page', right: 'Page') -> 'Page':
        new_page = Page(left.is_external() and right.is_external())
        # copy keys
        new_page.keys = left.keys
        new_page.keys.append(self.keys[ind])
        new_page.keys.extend(right.keys)
        # copy children
        new_page.children = left.children
        new_page.children.extend(right.children)

        self.children.pop(ind + 1)
        self.keys.pop(ind)
        self.children[ind] = new_page
        return new_page

    def borrow_from_left(self, kind: int, ind: int):
        left = self.children[ind - 1]
        cur = self.children[ind]
        # mirgate key
        cur.keys.insert(0, self.keys[kind])
        self.keys[kind] = left.keys[-1]
        left.keys.pop(len(left.keys) - 1)
        # migrate child
        if not cur.is_external():
            cur.children.insert(0, left.children[-1])
            left.children.pop(len(left.children) - 1)


    def borrow_from_right(self, ind: int):
        right = self.children[ind + 1]
        cur = self.children[ind]
        # migrate key
        cur.keys.append(self.keys[ind])
        self.keys[ind] = right.keys[0]
        right.keys.pop(0)
        # migrate child
        if not cur.is_external():
            cur.children.append(right.children[0])
            right.children.pop(0)

    def remove(self, key: KeyType) -> 'Page':
        left_upper_index = bisect_right(self.keys, SmartKey(key))
        if self.is_external(): # case 1
            if (left_upper_index > 0 and self.keys[left_upper_index - 1].key == key): 
                self.keys.pop(left_upper_index - 1)
            # else:
                # print(f'no key({key}) found in external node')
            return self
        # [10, 40]
        # [7, 9] [15, 35, 39] [45, 49, 90]
        ind = max(left_upper_index - 1, 0)
        if self.keys[ind].key == key: # case 2
            # wow we found key in page
            pred_ch = self.children[ind]
            succ_ch = self.children[ind + 1]
            if len(pred_ch.keys) >= DEGREE: # case A
                k = pred_ch.find_predecessor() 
                self.keys[ind] = k
                pred_ch.remove(k.key)
            elif len(succ_ch.keys) >= DEGREE: # case B
                k = succ_ch.find_successor() 
                self.keys[ind] = k
                succ_ch.remove(k.key)
            else: # case C
                merged = self.merge(ind, pred_ch, succ_ch)
                merged.remove(key)
                if len(self.keys) == 0:
                        return merged
                        
        else: # case 3
            needed_ch_ind = ind
            if key > self.keys[ind].key:
                needed_ch_ind += 1
            ch = self.children[needed_ch_ind]
            if len(ch.keys) == DEGREE - 1: # case A
                # try to grub from right sibling
                if (needed_ch_ind + 1 < len(self.children) and len(self.children[needed_ch_ind + 1].keys) > DEGREE - 1):
                    self.borrow_from_right(needed_ch_ind)
                elif (needed_ch_ind > 0 and len(self.children[needed_ch_ind - 1].keys) > DEGREE - 1):
                    self.borrow_from_left(ind, needed_ch_ind)
                else: # case B
                    merged = self.merge(ind, self.children[ind], self.children[ind + 1])
                    merged.remove(key)
                    if len(self.keys) == 0:
                        return merged
                # try one more time, now it should get to another branch
                self.remove(key)
            else:
                ch.remove(key)
        
        return self



class BTree:

    def __init__(self) -> None:
        """
            sentinel key should be less then any other keys
        """
        self.root = Page(True)

    def add_key_value(self, key: SmartKey) -> None:
        self._put(self.root, key)
        if self.root.is_full():
            left = self.root
            k, right = self.root.split()
            
            self.root = Page(False)
            self.root.keys = [k]
            self.root.children = [left, right]

    def find_key(self, key: SmartKey) -> SmartKey:
        return self.root.find(key)

    def remove(self, key: SmartKey) -> None:
        self.root = self.root.remove(key.key)

    def print_tree(self, deep: int = 0) -> None:
        """Print an level-order representation."""
        this_level = [self.root]
        while this_level:
            next_level = []
            output = ""
            for node in this_level:
                if node.children:
                    next_level.extend(node.children)
                output += str(list(map(lambda f: f.key, node.keys))) + " "
            print(output)
            this_level = next_level

    def _put(self, page: Page, key: SmartKey) -> None:

        if (page.is_external() or key in page.keys):
            page.add_key_value(key.key, key.value)
            return
        
        nxt = page.next(key)
        self._put(nxt, key)
        if nxt.is_full():
            page.split_and_add_page(nxt)
        
        nxt.close()
    

class NaiveTreeIndex:
    """
        Tree for functional testing. It based on python 'dict'.
    """
    def __init__(self, *args, **kwargs) -> None:
        self.tree: dict = {}

    def add_key_value(self, key: SmartKey):
        if key.key in self.tree:
            self.tree[key.key].append(key.value)
        else:
            self.tree[key.key] = [key.value]

    def find(self, key: SmartKey) -> T:
        return  self.tree[key.key] if key.key in self.tree else None

    def remove(self, key: SmartKey) -> None:
        if key.key in self.tree:
            self.tree.pop(key.key)

class NaiveListIndex:
    """
        Index for comparing performance of btree. Works on python lists
    """

    def __init__(self, *args, **kwargs):
        self.list = []
    
    def add_key_value(self, key: SmartKey):
        for k, v in self.list:
            if k == key.key:
                v.append(key.value)
                return 
        self.list.append((key.key, [key.value]))


    def find_key(self, key:SmartKey):
        for k, v in self.list:
            if k == key.key:
                return self.list[k]

        return None
        

from random import shuffle, randint, choice
import time


if __name__ == "__main__":

    if True:
        btree = BTree()
        naive = NaiveTreeIndex()

        iterations = 100000
        maxint = 150000

        inserts, deletions, finds = 0, 0, 0

        incorrect_finds = 0
        incorrect_deletions = 0

        for i in range(iterations):
            action = randint(1, 3)
            if action == 1: # add
                k, v = randint(1, maxint), randint(1, maxint)
                naive.add_key_value(SmartKey(k,v))
                btree.add_key_value(SmartKey(k, v))
                inserts += 1
            elif (action == 2 and len(naive.tree.keys()) > 0): # find
                key = SmartKey(choice(list(naive.tree.keys())))
                btree_res = btree.find_key(key)
                naive_res = naive.find(key)
                if btree_res != naive_res:
                    incorrect_finds += 1
                finds += 1
            elif len(naive.tree.keys()) > 0: # delete
                key = SmartKey(choice(list(naive.tree.keys())))
                btree.remove(key)
                naive.remove(key)
                if btree.find_key(key) != None:
                    incorrect_deletions += 1
                deletions += 1

        print(iterations, 'iterations proceeded')
        print(incorrect_finds, 'incorrect finds from', finds)
        print(incorrect_deletions, 'incorrect deletions from', deletions)
        exit(0)

    if True:
        nums = [13, 8, 3, 2, 5, 1, 1]
        btree = BTree()
        naive = NaiveTreeIndex()
        
        nums_k_v = [(nums[i], i) for i in range(len(nums))]
        n = 15000
        maxint = 15000
        
        nums_k_v = [(randint(1, maxint), i) for i in range(n)]
        shuffle(nums_k_v)
        # nums_k_v = [(8, 5), (10, 2), (7, 12), (13, 11), (9, 9), (11, 10), (11, 0), (2, 4), (11, 13), (5, 7), (8, 14), (13, 6), (5, 8), (6, 1), (14, 3)]
        print(nums_k_v)

        for k,v in nums_k_v:
            print('adding', k, v)
            btree.add_key_value(SmartKey(k, v))
            # btree.print_tree()
            naive.add_key_value(SmartKey(k, v))
        
        shuffle(nums_k_v)
        delete_n = n // 2

        for k,v in nums_k_v[:delete_n]:
            print('deleting', k, v)
            btree.remove(SmartKey(k))
            naive.remove(SmartKey(k))
            # btree.print_tree()
            # print('bt', btree.find_key(SmartKey(k)) == naive.find(SmartKey(k)).value)
            # print(k, btree.find_key(SmartKey(k)), naive.find(SmartKey(k)).value)
        # print('nv:',)
        cnt = 0
        for k,v in nums_k_v:
            v = btree.find_key(SmartKey(k)) == naive.find(SmartKey(k))
            print('bt', v)
            if not v:
                cnt += 1
            # print(k, btree.find_key(SmartKey(k)), naive.find(SmartKey(k)))
        print('nv:', cnt)
        exit(0)

    n = 10000
    maxint = 100
    
    nums_k_v = [(i, randint(1, maxint)) for i in range(n)]
    # cp = nums[:]
    # shuffle(nums)
    # print("nums order is folowing:", nums) 

    btree = BTree()
    naive = NaiveTreeIndex()
    naiveL = NaiveListIndex()

    st = time.time()
    for k,v in nums_k_v:
        btree.add_key_value(SmartKey(k, v))

    et = time.time();
    print('btree build:', et - st)

    st = time.time()
    for k,v in nums_k_v:
        naive.add_key_value(SmartKey(k, v))
    et = time.time();
    print('naive build:', et - st)

    st = time.time()
    for k,v in nums_k_v:
        naiveL.add_key_value(SmartKey(k, v))
    et = time.time();
    print('naive list build:', et - st)



    cp = nums_k_v[:]
    shuffle(cp)

    st = time.time()
    for k, _ in cp:
        naive.find(SmartKey(k))

    et = time.time();


    print('naive:', et - st)


    st = time.time()
    for k, _ in cp:
        btree.find_key(SmartKey(k))


    et = time.time();

    print('btree:', et - st)

    st = time.time()
    for k, _ in cp:
        naiveL.find_key(SmartKey(k))


    et = time.time();

    print('naive list:', et - st)
    # cnt = 0
    # for k, _ in cp:
    #     s = btree.find_key(SmartKey(k))
    #     ns = naive.find(SmartKey(k))
    #     if not ns:
    #         print('naive failed')
    #         print(k)
    #         continue
    #     if not s:
    #         print('btree failed')
    #         print(k)
    #         continue
    #     if ns.value == s.value:
    #         print("ok")
    #     else:
    #         cnt += 1
    #         print(k, 'naive:', ns.value, 'btree:', s.value)
    # print(cnt)