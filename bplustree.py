"""
B+tree implementation.
======================
B+ trees are an efficient index structure for mapping
a dictionary type object into a disk file.  All keys for
these dictionary structures are strings with a fixed
maximum length.  The values can be strings or 
integers (often representing seek positions in a secondary
file) depending on the implementation.

B+ trees can be useful for storing large mappings on disk
in such a way that a small number of keys/values can be
retrieved very quickly (with very few disk accesses).
B+ trees can also be useful for sorting a very large number
(millions) of records by unique string key values.

In this implementation all keys must 
not exceed the maximum length for a
given tree.  For string values there is no limitation on
size of content.  Note that in my tests updates are
2-3 times slower than retrieves, except for walking
which is much faster than normal retrieves.

As an add-on this module also provides a dbm compatible
interface that permits arbitrary length keys and values.
See below.

Provided here are several implementations:

BplusTree():
  defines a mapping from strings to integers.

caching_BPT():
  subclass of BplusTree that caches key,value
  pairs already seen.  This one cannot be updated.
  Construct a compatible index file using BplusTree
  and for read only access that touches a manageable
  number of keys, reopen the file using caching_BPT.

SBplusTree():
  defines a mapping from strings to strings.
  Updatable, but overwrites or deletions will
  leave "unreachable garbage" in the "value space"
  of the index file.  Use recopy_sbplus() to
  recopy the file, eliminating the garbage.

caching_SBPT():
  analogous to caching_BPT, but mapping to strings.

File creation:
==============
To create an index file do the following:

  file = open(filename, "w+b")
  B = SBplusTree(file, seek_position, nodesize, keymax)
  B.startup()

where seek_position is the seek_position where to "start"
the tree (usually the start of file, 0), nodesize is the
number of keys to keep at each node of the tree (pick an
even number between 2 and 255), and keymax is the maximum
size for the string keys in the mapping.

When choosing nodesize remember that larger nodesizes
make Python do more work and the file system do less work.
I think 212 is probably a pretty good number.  Of course
choose keymax to be as large as you will need.  A too large
key size, however, may waste considerable space in the file.

Now that you have a tree you can populate it with values
just like a dictionary.

   B["this"] = "that"
   B["willy"] = "wonka"
   x = B["this"]
   del B["this"]
   print len(B)
   ...
   f.close()

The supported dictionary operations are indexed retrieval
B[k], indexed assignment B[k] = v, key deletion del B[k] and
length len(B).  Retrieval and deletion will raise KeyError
on absent key.  Assignment will raise ValueError if the key
is too large.

B.keys(), B.values(), B.items() are not directly
supported, but see "Walking" below.

Note that the "basic" B-plus tree implementations only accept and
return integers as values.  The SB-plus implementation will
accept anything as values, but will use the str(x) function
to convert them to a string before storing the value in the
file.  The value returned will always be the string value
stored.  IE

   B["okeydoke"] = 23
   print `B["okeydoke"]`

prints "'23'", with the quotes.  The controlling 
application must control the
serialization/deserialization of values if it needs to store
something other than strings.

Read only file access:
======================
Once an index file exists it can be re-opened in "read only"
mode.

   f = open(filename, "rb")
   B = caching_SBPT(f)
   B.open()
   print B["willy"]

Note that the configuration parameters for the tree are
determined from a "file header".  Note however that a file
written to store integers using BplusTree should not be opened
for strings using SBplusTree or undefined and undesirable
behaviour will result.  Opening an SBplusTree as a BplusTree
is not advisable either.

If the seek position for the start of the tree is anything
other than 0, it must be specified:

   B = caching_SBPT(f, position)

or undefined behaviour will result.

In this mode, retrieval and walking are permitted, but attempts
to modify the structure will cause an exception.  In this mode the
programmer may prefer to use the "caching" versions if they expect
to retrieve the same keys many times and if the number of keys to
touch is not huge (say, in the millions).

Re-open for modification:
=========================
An existing index file can also be reopened for modification.

   f = open(filename, "r+b")
   B = SBplusTree(f)
   B.open()
   B["this"] = "is fun!"
   ...
   f.close()

Again, modifications are disallowed for cached trees.

Walking:
========
One of the neat features of B-plus trees is that they keep
their keys in sorted order.  Hence it is easy and efficient
to retrieve the keys/values sorted by the keys, and also to
do range queries.

To support this feature the tree implementations provide
a "walker" interface.

   walker = tree.walker(lowerkey, includelower, 
                        upperkey, includeupper)
   while walker.valid:
      print (walker.current_key(), walker.current_value())
      walker.next()
   walker.first()

Or to traverse all pairs in key-sorted order

   walker = tree.walker()
   while walker.valid:
      print (walker.current_key(), walker.current_value())
      walker.next()
   walker.first()

The lowerkey/upperkey parameters indicate where to start/end
walking (interpreted as the beginning/end if they are
omitted or set to None) and includelower indicates whether
to include the lower value if it is present in the tree,
if not the next greater key will be the start position.

For example to walk from key "m" (or just past it if absent)
to the end:

    w = tree.walker("m", 1)

or to walk between "mzzz" and "nzzz" not inclusive:

    w = tree.walker("mzzz", 0, "nzzz", 0)

or walk from the beginning to "m", not inclusive

    w = tree.walker(None, None, "m", 0)

Here w.current_key() and w.current_value() retrieve the current
key and value respectively, w.next() moves to the next pair, if there is one
and w.valid indicates whether there is a current pair, and 
w.first() resets the walker to the first pair, if there is one.
At initialization the walker is already at the first pair, if
it exists.

Multiaccess optimizations:
==========================

To make updates and retrievals run faster you can enable/disable
a tree-global least-recently-used fifo mechanism which reduces
reads and writes, but be *sure* to disable it before closing any
BTree file that has been modified, or the tree may well become
corrupt

    try:
       B.enable_fifo()
       do_updates(B)
    finally:
       B.disable_fifo()

The fifo may also improve performance for read only access,
but it is not important to disable the mechanism later.
The optimizations help most when key accesses are localized.
(ie, a bunch of inserts with keys starting "abc..."
or 10000 inserts in [almost] key-sorted order).
For only one access, it's no help at all!  The fifo mechanism
will not help for walking, so don't do it if you will only walk
a portion of the tree once.  You might want to try putting
various values as the optional argument to enable_fifo, eg, 
B.enable_fifo(1000) (but that's probably past the diminishing returns
point...).  Large fifos will consume lots of "core" memory.

Trash compacting
================

The functions recopy_bplus(f1, f2) and recopy_sbplus(f1, f2)
recopy open "rb" file f1 to (open "w+b")
file f2 for BplusTrees and SBplusTrees respectively.  The
copy f2 will have no "garbage" and almost all leaf nodes will be
full.  This can result in reducing file size by about 1/3.
Both files must have headers at seek 0 and hold nothing but
the tree nodes and tree data.  Also look at recopy_tree(t1, t2).

DBM compatibility
=================

As an application of SBplusTree this module also provides
a plug-compatible implementation of the standard python dbm
style functionality, except that the "mode" parameter is not
supported on initialization.  See the Python Lib manual entry
on dbm.  Both keys and values may be of *arbitrary* length in
this case, but keys are not kept in key-sorted order and
overwrites and key collisions will result in unused garbage
in the file (keys and values occur as SBplustree "values"
using a PORTABLE bucket hashing scheme).

   d = dbm(filename, flag)
   
creates a dictionary like structure with d[key]=value, x=d[key],
d.has_key(key), del d[key], len(d), and d.keys().  Also
after any modification be sure that d gets explicitly
closed d.close() or the file *may* become corrupt.
Also, d.copy(otherfilename, "c") will create a more
compact copy of d in another file with garbage discarded.
The dbm implementation uses a very large fifo, so many accesses
may consume a lot of "core" memory.

DBM comparison
==============
An alternative to this module is gdbm or dbm for file
indexing -- both supported by available Python extension
modules.

Expect dbm to be generally faster than this module, but
remember:
  - dbm doesn't do key-sorted walking.
  - dbm often isn't portable across machines.
  - dbm isn't written in Python (ie, requires an extension
    module).
  - dbm sometimes doesn't allow arbitrary value lengths
    (but gdbm allows arbitrary length keys and values...)
whereas this module does/is.  I don't know precisely how
much faster dbm is, but for some types of use it may turn
out to actually be slower, for all I know.  Please let
me know!  Probably the most compelling advantage is that
the index files generated by this module are portable across
platforms.

Fun
===
For fun or debugging try tree.dump().
There is also a test suite for the module at the
bottom (test() and retest()) which create a test index
called "test" in the current directory.  Also testdbm().

Caveats:
========
NOTE: only the standard string ordering is supported for
  walking at present.  This could be fixed...

WARNING: Never modify a tree while it is being walked.  Always
  recreate all walkers after a tree modification.
  NEVER open the same tree for modification twice!
  ALWAYS make sure a modified tree has disabled the fifo and
  the file has been closed before reopening the tree.

WARNING: This implementation has no support for concurrent
  modification.  It is designed for "write once by one process",
  "read many by (possibly) several processes, but not with
  concurrent modification."

WARNING: If during modification any exception other than a KeyError/ValueError
  is not caught, the indexed file structure *may* become corrupt (because
  some operations completed and others didn't).  Walking all values
  of an index or B.dump() may detect some corrupt states (***Note I should write
  a sanity-check routine***)

WARNING: As noted above an overwrite or delete for a SBTree (mapping
  to strings) will leave unreachable junk in the "value space" of
  the index.  See above.

This code is provided for arbitrary use, but without warrantee of
any kind.  At present it seems to work, but I'll call it an beta
until it's better tested.

Aaron Watters, arw@pythonpros.com
http://starship.skyport.net/crew/aaron_watters
http://www.pythonpros.com
"""

import string

nilseek = -1

from marshal import dumps
sequence_overhead = len(dumps(""))
intsize = len(dumps(1))

# bisect algorithm with bounds (in 1.5 this is in /Lib)
# Insert item x in list a, and keep it sorted assuming a is sorted

def insort(a, x, lo=0, hi=None):
     if hi is None:
        hi = len(a)
     while lo < hi:
        mid = (lo+hi)/2
        if x < a[mid]: hi = mid
        else: lo = mid+1
     a.insert(lo, x)


# Find the index where to insert item x in list a, assuming a is sorted

def bisect(a, x, lo=0, hi=None):
     if hi is None:
        hi = len(a)
     while lo < hi:
        mid = (lo+hi)/2
        if x < a[mid]: hi = mid
        else: lo = mid+1
     return lo


NOROOMERROR = "NOROOMERROR"
    
Rootflag = 1
Interiorflag = 2
Freeflag = 3
Leafflag = 4
LeafandRootflag = 5
Leafflags = (Leafflag, LeafandRootflag)
Interiorflags = (Interiorflag, Rootflag)

class Node_Fifo:
   """fifo of nodes for locality access optimization"""
   def __init__(self, size=30):
       self.fifo = [] # fifo of active nodes, if used.
       self.fifosize = size
       self.fifo_dict = {}

   def flush_fifo(self):
       for node in self.fifo:
           if node.dirty:
              node.store(1)
       self.fifo = []
       self.fifo_dict = {}

class Node:
   """B+ tree node.
      follows Silberchatz & Korth database intro book closely.
      Each node has a number self.validkeys> 1 of valid keys (except for
      a tree with only 0 or 1 entries.  For leaves each
         self.key[i] that is valid is associated with int value
         self.indices[i]
      For nonleaves nextnode integer reference is at
         self.indices[i+1] and
         self.indices[0]
      is for entries with keys<self.keys[0]
      for leaves self.indices[self.size] is "pointer" to
      next sequential leaf.
   """

   # for update optimization
   dirty = 0
   fifo = None
   
   def __init__(self, flag, size, keylen, position, infile, cloner=None):
       self.flag = flag # one of Rootflag...
       self.size = size # num of pointers from this Node
       #if size>255: raise ValueError, "size too large: "+`size`
       if size<0: #or size%2==1: 
          raise ValueError, "size must be positive <= 255"
       self.position = position # seek position in file
       self.infile = infile # open file for storage
       self.keylen = keylen # maximum key length (no nulls!)
       # seek pointers for descendents (root/interior)
       # all but last is a value for a leaf, last is successor seek
       self.indices = [-1] * (size+1)
       # key storage
       # for leaves value for key[i] is at indices[i]
       # for others keys[i] is at indices[i+1],
       #   indices[0] points to keys preceding keys[0].
       # for freelist nodes, nodes are stored on
       #   linked list with indices[0] forward
       self.keys = [""] * size
       # linearized storage length in file
       #self.intstorage = intsize * (size+1)
       #self.keystorage = keylen * size
       # in debug mode the seek position is prepended
       #if debug:
       #   self.intstorage = self.intstorage + intsize
       #self.storage = (2 +           # flag, valid
       #                self.intstorage + self.keystorage)
       if cloner is None:
          self.storage = (sequence_overhead + # list overhead
                       2*intsize +         # flag, valid
                       (size+1)*intsize +  # indices
                       size*(sequence_overhead + keylen) # keys
                       )
       else:
          self.storage = cloner.storage
          self.fifo = cloner.fifo
       # note, for interior nodes
       #    validkey of 0 means one valid pointer, -1 means none
       # for leaves validkeys should be positive
       if flag in [Interiorflag, Rootflag]:
          self.validkeys = -1 # number of valid entries
       else:
          self.validkeys = 0
          
   def clear(self):
       # reinitialize keys, indices for self.
       size = self.size
       self.keys = [""] * size
       self.validkeys = 0
       if self.flag in Interiorflags:
          # reinit all indices
          self.indices = [-1] * (size+1)
          self.validkeys = -1
       else:
          # don't clobber forward pointer
          self.indices[:size] = [-1] * size
       
   # interior node operation.
   def putnode(self, key, node):
       """place a node for key into self.  Raise NOROOMERROR if no room."""
       from types import StringType
       if type(key)!=StringType:
          raise TypeError, "bad key "+`key`
       position = node.position
       self.putposition(key, position)
       
   def putfirstindex(self, index):
       #print "putfirstindex", index
       if self.validkeys>=0:
          raise ValueError, "putfirstindex on full node"
       self.indices[0] = index
       self.validkeys = 0
       
   def putposition(self, key, position):
       #print "putposition", (key, position), self.indices, self.keys
       if self.flag not in Interiorflags:
          raise ValueError, "cannot insert into leaf node"
       validkeys = self.validkeys
       last = validkeys + 1
       if self.validkeys>=self.size: raise NOROOMERROR, "no room"
       # store the key
       if validkeys<0: # no nodes currently
          #print "no keys"
          self.validkeys = 0
          self.indices[0] = position
       else:
          # yes nodes
          keys = self.keys
          # is the key there already?
          if key in keys:
             if keys.index(key)<validkeys:
                raise ValueError, "reinsert of node for existing key"
          place = bisect(keys, key, 0, validkeys)
          keys.insert(place, key)
          del keys[last]
          # store the index
          indices = self.indices
          #print "inserting", position, "before", indices
          indices.insert( place+1, position)
          del indices[last+1]
          #print "after", indices
          self.validkeys = last
       
   def delnode(self, key):
       """delete node for key, (key==None means "start" node)
          key must match exactly."""
       if self.flag not in Interiorflags:
          raise ValueError, "cannot delete node from leaf node"
       if self.validkeys<0: raise KeyError, "no such key (empty)"
       validkeys = self.validkeys
       indices = self.indices
       keys = self.keys
       #print "delnode before", key, keys, indices, validkeys
       if key is None:
          # delete first node (shouldn't happen?
          place = 0
          indexplace = 0
       else:
          # delete non-first node
          place = keys.index(key)
          indexplace = place+1
       del indices[indexplace]
       indices.append(nilseek)
       del keys[place]
       keys.append("")
       #keys[validkeys-1] = ""
       #print "delnode after", keys, indices
       self.validkeys = validkeys-1
       
   def get_keys(self):
       """return a list of valid keys for self."""
       validkeys = self.validkeys
       if validkeys<=0: return []
       else: return self.keys[0:validkeys]
       
   def keys_indices(self, leftmost):
       """return [(leftmost, firstindex), (nodekey, nodeindex), ...]"""
       keys = self.get_keys()
       if self.flag in Interiorflags:
          # nonleaf, must add leftmost to complete keys
          keys = [leftmost] + keys
       indices = self.indices[:len(keys)]
       # return pairing
       return map(None, keys, indices)
              
   def getnode(self, key):
       """get node that exactly matches key (None for first)"""
       if self.flag not in Interiorflags:
          raise ValueError, "cannot getnode from leaf node"
       if key is None: index = 0
       else: index = self.keys.index(key) + 1
       place = self.indices[index]
       if place<0: raise IndexError, "invalid position! "+`(place, key)`
       # short-circuit optimization: check fifo
       fifo = self.fifo
       if fifo:
          ff = fifo.fifo
          fd = fifo.fifo_dict
          if fd.has_key(place):
             node = fd[place]
             ff.remove(node)
             ff.insert(0, node)
             return node
       node = self.clone(place)
       node = node.materialize()
       return node
       
   # leaf mode operations
   def next(self):
       """get next node from self in linear leaf sequence, or return None."""
       if self.flag not in Leafflags:
          raise ValueError, "cannot get next for non-leaf."
       place = self.indices[self.size]
       if place == nilseek: return None
       else:
          node = self.clone(place)
          node = node.materialize()
          return node
          
   def putvalue(self, key, value):
       """put key->value mapping into leaf node.
       """
       from types import StringType, IntType
       if type(key)!=StringType and type(value)!=IntType:
          raise ValueError, "bad key, value"+ `(key,value)`
       if self.flag not in Leafflags:
          raise ValueError, "cannot get next for non-leaf."
       validkeys = self.validkeys
       indices = self.indices
       keys = self.keys
       if validkeys<=0:  # empty
          # "first entry", (key, value)
          indices[0] = value
          keys[0] = key
          self.validkeys = 1
       else:
          place=None
          if key in keys:
             place = keys.index(key)
             if place>=validkeys: place=None
          if place is not None:
             keys[place] = key
             indices[place] = value
          else:  
             if validkeys>=self.size: 
                print "node out of room"
                #for x in self.__dict__.items(): print x
                #raise NOROOMERROR, "no room"
             place = bisect(keys, key, 0, validkeys)
             #print "next entry at", place
             #next = place+1
             last = validkeys+1
             del keys[validkeys]
             del indices[validkeys]
             keys.insert(place, key)
             indices.insert(place, value)
             self.validkeys = last
             

   def put_all_values(self, keys_indices):
       """optimization for node restructuring."""
       self.clear()
       indices = self.indices
       keys = self.keys
       length = self.validkeys = len(keys_indices)
       if length>self.size:
          raise IndexError, "bad length "+`length`
       #if length<self.size/2-1: # not valid for delete (?)
       #   raise IndexError, "not enough keys"+`length`
       for i in xrange(length):
           (keys[i], indices[i]) = keys_indices[i]
           
   def put_all_positions(self, first_position, keys_positions):
       """optimization for restructuring."""
       self.clear()
       indices = self.indices
       keys = self.keys
       length = self.validkeys = len(keys_positions)
       if length>self.size:
          raise IndexError, "bad length "+`length`
       #if length<self.size/2: # not valid for delete (?)
       #   raise IndexError, "not enough keys"+`length`
       indices[0] = first_position
       for i in xrange(length):
           (keys[i], indices[i+1]) = keys_positions[i]

   def delvalue(self,key):
       keys = self.keys
       indices = self.indices
       if key not in keys:
          raise KeyError, "missing key, can't delete"
       place = keys.index(key)
       validkeys = self.validkeys
       #next = place + 1
       prev = validkeys -1
       #keys[place:prev] = keys[next:validkeys]
       #indices[place:prev] = indices[next:validkeys]
       del keys[place]
       del indices[place]
       keys.insert(prev, "")
       indices.insert(prev, nilseek)
       self.validkeys = validkeys-1
       #keys[prev] = ""
       #indices[prev] = nilseek
          
   def getvalue(self, key):
       """get value exactly matching key."""
       try:
           place = self.keys.index(key)
       except ValueError:
           raise KeyError, "key not found: " + `key`
       else:
           return self.indices[place]
          
   def newneighbor(self, position):
       """make a new leaf adjacent to self"""
       if self.flag not in Leafflags:
          raise ValueError, "cannot make leaf neighbor for non-leaf."
       neighbor = self.clone(position)
       size = self.size
       indices = self.indices
       neighbor.indices[size] = indices[size]
       indices[size] = position
       return neighbor

   def nextneighbor(self):
       """return next leaf in tree, or None."""
       if self.flag not in Leafflags:
          raise ValueError, "cannot get leaf neighbor for non-leaf."
       size = self.size
       position = self.indices[size]
       if position==nilseek:
          return None
       else:
          neighbor = self.clone(position)
          neighbor = neighbor.materialize()
          return neighbor
       
   def delnext(self, next, free):
       #print "delnext"
       #print self.indices, self.position
       #print next.indices, next.position
       size = self.size
       if self.indices[size]!=next.position:
          raise ValueError, "invalid next pointer"
       self.indices[size] = next.indices[size]
       return next.free(free)
       
   # free list mode operations
   def free(self, freenodeposition):
       """add self to free list, return position as new
          free position."""
       self.flag = Freeflag
       self.indices[0] = freenodeposition
       self.store()
       return self.position
       
   def unfree(self, flag):
       """Assuming self is head of free list,
          pop self off freelist, return next free elt position
          DOES NOT STORE.
          """
       next = self.indices[0]
       self.flag = flag
       self.validkeys = 0
       self.indices[0] = nilseek
       self.clear()
       return next
          
   def clone(self, position):
       """return a Node of same shape as self."""
       if self.fifo:
          dict = self.fifo.fifo_dict
          if dict.has_key(position):
             return dict[position]
       return Node(self.flag, self.size, self.keylen,
                   position, self.infile, self)
                   
   def getfreenode(self, freeposition, freenode_callback=None):
       """get free node of same shape as self from self.file
          make one if none exists.  Assume freeposition is
          seek position of next free node.
          returns (node, newfreeposition)
          if freenode_callback is specified, it is a function to call
          with a new free list head, if needed freenode_callback(int)
          """
       file = self.infile
       if freeposition==nilseek:
          # add at last position in file
          #save = file.tell()
          file.seek(0, 2)  # goto eof
          position = file.tell()
          thenode = self.clone(position)
          thenode.store() # write new record
          #file.seek(save)
          return (thenode, nilseek)
       else:
          # get node at position
          position = freeposition
          thenode = self.clone(position)
          thenode = thenode.materialize() # get old node
          next = thenode.indices[0]
          if freenode_callback is not None:
             freenode_callback(next)
          thenode.__init__(self.flag, self.size, 
             self.keylen, position, self.infile)
          thenode.store() # save reinitialized node
          return (thenode, next)
       
   def materialize(self):
       """read self from file."""
       #print "materialize", self.position
       position = self.position
       if self.fifo:
          fifo = self.fifo
          # look in fifo
          dict = fifo.fifo_dict
          ff = fifo.fifo
          if dict.has_key(position):
             #print "using fifo", position
             node = dict[position]
             if node is not ff[0]:
                ff.remove(node)
                ff.insert(0, node)
             #if len(ff)!=len(dict): raise "whoops"
             return node
       f = self.infile
       #f.flush() # ? needed ?
       #save = f.tell()
       f.seek(position)
       data = f.read(self.storage)
       self.delinearize(data)
       #f.seek(save) # go back
       if self.fifo:
          self.add_to_fifo()
       return self
       
   def add_to_fifo(self):
          fifo = self.fifo
          ff = fifo.fifo
          dict = fifo.fifo_dict
          #if len(dict)!=len(ff): raise "whoops before"
          position = self.position
          if dict.has_key(position):
             old = dict[position]
             del dict[position]
             ff.remove(old)
          dict[self.position] = self
          #if self in ff: ff.remove(self)
          ff.insert(0, self)
          if len(ff)>self.fifo.fifosize:
             last = ff[-1]
             del ff[-1]
             del dict[last.position]
             #print "storing", last.position
             if last.dirty:
                last.store(1)
          #if len(dict)!=len(fifo): raise "whoops"
             
   def enable_fifo(self, size = 33):
       "you better disable it later!"
       if size<5 or size>1000000:
          raise ValueError, "size not valid: "+`size`
       self.fifo = Node_Fifo(size)
       
   def disable_fifo(self):
       #print "disabling fifo", self.fifo_dict.keys()
       #global fifo_on
       if self.fifo:
          self.fifo.flush_fifo()
          self.fifo = None
       
   def store(self, force=0):
       """write self to file at self.position
          return end of record seek position."""
       #print "store", self.position
       position = self.position
       fifo = self.fifo
       if not force and fifo:
          fd = fifo.fifo_dict
          if fd.has_key(self.position) and fd[position] is self:
             self.dirty = 1
             return # defer
       f = self.infile
       #save = f.tell()
       f.seek(position)
       data = self.linearize()
       f.write(data)
       last = f.tell()
       #f.seek(save)
       self.dirty = 0
       if not force and self.fifo:
          self.add_to_fifo()
       return last
       
   def linearize(self):
       """create record format for self."""
       from marshal import dumps
       all = [self.flag, self.validkeys] + self.indices + self.keys
       s = dumps(all)
       ls = len(s)
       storage = self.storage
       if (ls > storage):
          raise ValueError, "bad storage: " + `s`
       s = s + "X" * (storage-ls)
       return s
       
       #indices = self.indices
       # in debug prepend seek position
       #if debug: indices = [self.position] + indices
       #ints = encodeints(indices)
       #keys = encodestrs(self.keys, self.keylen)
       #validkeys = self.validkeys
       #if validkeys<0: v = "*" # dummy purposes only (prewrites)
       #else: v = chr(self.validkeys ^ CMASK) # try to make v readable
       #return "%s%s%s%s%s" % (self.flag, v, ints, keys, SEPARATOR)
       
   __print__ = linearize
       
   def delinearize(self, str):
       """parse, store from record format from self."""
       from marshal import loads
       all = loads(str)
       [self.flag, self.validkeys] = all[:2]
       #self.flag = chr(ordflag)
       s = self.size
       next = 2+s+1
       indices = self.indices = all[2:next]
       keys = self.keys = all[next:]
       if len(keys) != s:
          raise ValueError, "bad keys: " + `keys` + `len(keys)`
         
   def dump(self, indent=""):
       flag = self.flag
       if flag==Freeflag:
          print 'free->', self.position,
          nextp = self.indices[0]
          if nextp!=nilseek:
             next = self.clone(nextp)
             next = next.materialize()
             next.dump()
          else:
             print "!last"
          return
       nextindent = indent + "   "
       print indent,
       if flag == Rootflag: print "root",
       elif flag == Interiorflag: print "interior",
       elif flag == Leafflag: print "leaf", 
       elif flag == LeafandRootflag: print "root and leaf",
       else: print "invalid flag???", flag,
       print self.position, "valid=", self.validkeys
       print indent, "keys", self.keys
       print indent, "seeks", self.indices
       if flag in [Rootflag, Interiorflag]:
          # interior
          for i in self.indices:
              if i != nilseek:
                 n = self.clone(i)
                 n = n.materialize()
                 n.dump(nextindent)
       else:
          # leaf
          pass
       print indent, "*****"
       
class BplusTree:
   """Basic B+tree maps fixed length strings to integers
      (could be seek positions)"""

   length = None # fill in later
   
   dirty = 0 # default
      
   # length keylen, nodesize, root_seek, free
   header_format = "%10d %10d %10d %10d %10d\n" 

   def __init__(self, infile, position=None, nodesize=None, keylen=None):
       """infile should be open file in "rb" or "w+b" mode.
          if optional args are not given they are determined
          from first line in file.
       """
       #print "BPlusTree(%s, %s, %s)" % (position, nodesize, keylen)
       if keylen is not None and keylen<=2:
          raise ValueError, "keylen must be greater than 2"
       self.root_seek = nilseek # dummy
       self.free = nilseek
       self.root = None
       self.file = infile
       self.nodesize = nodesize
       self.keylen = keylen
       if position is None:
          position = 0
       self.position = position
       #if nodesize is None:
       #   self.get_parameters()

   def walker(self, 
                      keylower=None, includelower=None,
                      keyupper=None, includeupper=None):
       return BplusWalker(self, keylower, includelower,
                                keyupper, includeupper)

   def init_params(self):
       return (self.file, self.position, self.nodesize, self.keylen)

   def getfile(self):
       return self.file

   def getroot(self):
       return self.root
          
   def update_freelist(self, position):
       if self.free!= position:
          self.free = position
          self.reset_header()

   def startup(self):
       """startup the file, write header, set root"""
       if self.nodesize is None or self.keylen is None:
          raise ValueError, \
           "cannot initialize without nodesize, keylen specified"
       self.length = 0
       self.reset_header()
       file = self.file
       file.seek(0,2) # goto eof
       self.root_seek = file.tell()
       self.reset_header()
       root = self.root = Node(LeafandRootflag, self.nodesize, self.keylen,
                        self.root_seek, file)
       root.store()

   def open(self):
       """get info on existing file."""
       file = self.file
       self.get_parameters()
       self.root = Node(LeafandRootflag, self.nodesize, self.keylen,
                        self.root_seek, file)
       self.root = self.root.materialize()
       

   fifo_enabled = 0
   
   def enable_fifo(self,size=33):
       #print "fifo enabled"
       self.fifo_enabled = 1
       self.root.enable_fifo(size)
       
   def disable_fifo(self):
       #print "fifo disabled"
       self.fifo_enabled = 0
       if self.dirty: 
          self.reset_header()
          self.dirty = 0
       self.root.disable_fifo()
 
   def reset_header(self):
       """reset the header of the file"""
       if self.fifo_enabled: 
          self.dirty = 1
          return # defer
       file = self.file
       file.seek(self.position)
       #file.write( self.header_format % 
       # (self.length, self.keylen, self.nodesize, self.root_seek, self.free) )
       from marshal import dump
       dump( (self.length, self.keylen, self.nodesize, self.root_seek, self.free),
             file)
          
   def get_parameters(self):
       file = self.file
       #save = file.tell()
       file.seek(self.position)
       from marshal import load
       temp = load(file)
       #print temp, self.position
       (self.length, self.keylen, self.nodesize, self.root_seek, self.free)=\
          temp
       #file.seek(save)

   def __len__(self):
       if self.length is None:
          self.get_parameters()
       return self.length
       
   def __getitem__(self, key):
       """self[key] -- get item associated with key"""
       if self.root is None: raise ValueError, "not open!"
       return self.find(key, self.root)

   def has_key(self, key):
       try:
           test = self[key]
       except KeyError:
           return 0
       else:
           return 1
       
   def __setitem__(self, key, value):
       """self[key]=value -- set map for key to value"""
       from types import StringType, IntType
       if type(key)!=StringType: raise ValueError, "key must be string"
       if type(value)!=IntType: raise ValueError, "value must be int"
       if len(key)>self.keylen: raise ValueError, "key too long"
       if value<0: raise ValueError, "value must be positive"
       current_length = self.length
       #if FORBIDDEN in key: 
       #   raise ValueError, "key cannot contain "+`FORBIDDEN`
       root = self.root
       if root is None: raise ValueError, "not open!"
       #global test1 #debug
       test1 = self.set(key, value, self.root)
       # do we need to split root?
       if test1 is not None:
          #print "splitting root", `test1`
          (leftmost, node) = test1
          #print "leftmost", leftmost, node
          # make a non-leaf root
          (newroot, self.free) = root.getfreenode(self.free)
          newroot.flag = Rootflag
          if root.flag is LeafandRootflag:
             root.flag = Leafflag
          else:
             root.flag = Interiorflag
          newroot.clear()
          newroot.putfirstindex(root.position)
          newroot.putnode(leftmost, node)
          self.root = newroot
          self.root_seek = newroot.position
          newroot.store()
          root.store()
          self.reset_header()
       else:
          if self.length!=current_length:
             self.reset_header()
       
   def __delitem__(self, key):
       """del self[key] -- remove map for key to value"""
       root = self.root
       currentlength = self.length
       self.remove(key, root)
       if root.flag==Rootflag:
          validkeys = root.validkeys
          if validkeys<1:
             if validkeys<0:
                raise ValueError, "invalid empty non-leaf root"
             newroot = self.root = root.getnode(None)
             self.root_seek = newroot.position
             self.free = root.free(self.free)
             self.reset_header()
             if newroot.flag==Leafflag:
                newroot.flag = LeafandRootflag
             else:
                newroot.flag = Rootflag
             newroot.store()
          elif self.length!=currentlength:
             self.reset_header()
       elif root.flag!=LeafandRootflag:
          raise ValueError, "invalid flag for root"
       elif self.length!=currentlength:
          self.reset_header()
       
   def set(self, key, value, node):
       """insert key-->value starting at node.
          return None if no split, else return
             (leftmostkey, newnode)
       """
       keys = node.keys
       validkeys = node.validkeys
       if node.flag in Interiorflags:
          # non leaf
          # find the descendent to insert in
          place = bisect(keys, key, 0, validkeys)
          #print place, key, validkeys, keys
          if place>=validkeys or keys[place]>=key:
             # insert at previous node
             index = place
          else:
             # index at node
             index = place+1
          if index==0: nodekey=None
          else: nodekey=keys[place-1]
          #print "nodekey", nodekey, node.indices
          nextnode = node.getnode(nodekey)
          test = self.set(key, value, nextnode)
          # split?
          if test is not None:
             (leftmost, insertnode) = test
             try:
                 # insert if room
                 node.putnode(leftmost, insertnode)
             except NOROOMERROR:
                 # no room, split
                 insertindex = insertnode.position
                 (newnode, self.free) = node.getfreenode(
                   self.free, self.update_freelist)
                 newnode.flag = Interiorflag
                 ki = node.keys_indices("dummy")
                 (dummy, firstindex) = ki[0]
                 # remove dummy
                 ki = ki[1:]
                 # insert new pair
                 insort(ki, (leftmost, insertindex))
                 newleftmost = self.divide_entries(firstindex, node, newnode, ki)
                 node.store()
                 newnode.store()
                 return (newleftmost, newnode)
             else:
                 node.store()
                 return None # no split
       else:
          # leaf
          if key not in keys or keys.index(key)>=validkeys:
              newlength = self.length+1
          else:
              newlength = self.length
          try:
              # insert if room
              node.putvalue(key, value)
          except NOROOMERROR:
              # no room: split
              # get entries (dummy is ignored for leaves)
              ki = node.keys_indices("dummy")
              insort(ki, (key, value))
              (newnode, self.free) = node.getfreenode(
                self.free, self.update_freelist)
              newnode = node.newneighbor(newnode.position)
              newnode.flag = Leafflag
              # 0 is dummy firstindex, ignored for leaves
              newleftmost = self.divide_entries(0, node, newnode, ki)
              node.store()
              newnode.store()
              self.length = newlength
              return (newleftmost, newnode)
          else:
              node.store()
              self.length = newlength
              return None
              
   def remove(self, key, node):
       """remove key from tree at node.
          raise KeyError if absent.
          return (leftmost, size) if leftmost changes.
          otherwise return (None, size).
          Caller is responsible for restructuring node, if needed.
       """
       newnodekey = None
       if node.flag in Interiorflags:
          # nonleaf
          keys = node.keys
          validkeys = node.validkeys
          place = bisect(keys, key, 0, validkeys)
          if place>=validkeys or keys[place]>=key:
             # delete at tree before place
             index = place
          else:
             # delete at tree for place
             index = place+1
          if index==0: nodekey=None
          else: nodekey=keys[place-1]
          nextnode = node.getnode(nodekey)
          # recursively remove from nextnode
          (lm, size) = self.remove(key, nextnode)
          # is nextnode now too small?
          nodesize = self.nodesize
          half = nodesize/2
          if (size<half):
             # restructure, ugly!
             # find another node for redistribution
             if nodekey is None and validkeys==0:
                raise IndexError, "invalid node, only one child!"
             if place>=validkeys:
                # final node, get previous
                rightnode = nextnode
                rightkey = nodekey
                if validkeys<=1: leftkey = None
                else: leftkey = keys[place-2]
                leftnode = node.getnode(leftkey)
             else:
                # non-final, get next
                leftnode = nextnode
                leftkey = nodekey
                if index==0: rightkey=keys[0]
                else: rightkey = keys[place]
                rightnode = node.getnode(rightkey)
             # get all keys, indices
             rightki = rightnode.keys_indices(rightkey)
             leftki = leftnode.keys_indices(leftkey)
             ki = leftki + rightki
             # redistribute or merge?
             #print "ki, nodesize", ki, nodesize
             lki = len(ki)
             if lki>nodesize or (leftnode.flag!=Leafflag and lki>=nodesize):
                # redistribute
                (newleftkey, firstindex) = ki[0]
                if leftkey==None:
                   newleftkey = lm
                if leftnode.flag!=Leafflag:
                   # nuke first ki
                   ki = ki[1:]
                newrightkey = self.divide_entries(
                     firstindex, leftnode, rightnode, ki)
                # delete, reinsert right
                node.delnode(rightkey)
                node.putnode(newrightkey, rightnode)
                # ditto for left if first changed
                if (leftkey!=None and leftkey!=newleftkey):
                   node.delnode(leftkey)
                   node.putnode(newleftkey, leftnode)
                node.store()
                leftnode.store()
                rightnode.store()
             else:
                # merge into left, free right
                (newleftkey, firstindex) = ki[0]
                #leftnode.clear()
                if leftnode.flag!=Leafflag:
                   #leftnode.putfirstindex(firstindex)
                   #del ki[0]
                   #for (k,i) in ki:
                   #    leftnode.putposition(k,i)
                   leftnode.put_all_positions(firstindex, ki[1:])
                else:
                   #for (k,i) in ki:
                   #    leftnode.putvalue(k,i)
                   leftnode.put_all_values(ki)
                if rightnode.flag==Leafflag:
                   self.free = leftnode.delnext(rightnode, self.free)
                else:
                   self.free = rightnode.free(self.free)
                if leftkey is not None and newleftkey!=leftkey:
                   node.delnode(leftkey)
                   node.putnode(newleftkey, leftnode)
                node.delnode(rightkey)
                node.store()
                leftnode.store()
                self.reset_header()
             if leftkey is None: newnodekey = lm
          else:
             # no restructure
             # update leftmost, if needed
             if nodekey is None: newnodekey = lm
             elif lm is not None:
                node.delnode(nodekey)
                node.putnode(lm, nextnode)
          # end of restructure if
       else:
          # leaf, base case: just delete it
          if node.validkeys<1:
             # should only happen for empty root
             raise KeyError, "no such key"
          first = node.keys[0]
          node.delvalue(key)
          rest = node.keys[0]
          if first!=rest:
             newnodekey = rest
          node.store()
          self.length = self.length - 1
       return (newnodekey, node.validkeys)

   def divide_entries(self, firstindex, node1, node2, entries):
       """divide presorted entries evenly among node1, node2
          return leftmost of node2.
          firstindex is ignored for leaves
       """
       middle = len(entries)/2 + 1
       #node1.clear()
       #node2.clear()
       if node1.flag in Interiorflags:
          #middle = middle+1
          left = entries[:middle]
          right = entries[middle:]
          #print "left, right", left, right
          # nonleaf
          #node1.putfirstindex(firstindex)
          #for (k,i) in left:
          #    node1.putposition(k,i)
          (leftmost, midindex) = right[0]
          #node2.putfirstindex(midindex)
          #for (k,i) in right[1:]:
          #    node2.putposition(k, i)
          node1.put_all_positions(firstindex, left)
          node2.put_all_positions(midindex, right[1:])
          return leftmost
       else:
          # leaf
          left = entries[:middle]
          right = entries[middle:]
          #for (k,i) in left:
          #    node1.putvalue(k,i)
          #for (k,i) in right:
          #    node2.putvalue(k,i)
          node1.put_all_values(left)
          node2.put_all_values(right)
          return right[0][0]
       
   def find(self, key, node):
       """find key starting at node."""
       while node.flag in Interiorflags:
          # non-leaf
          thesekeys = node.keys
          validkeys = node.validkeys
          # find place at or just beyond key
          place = bisect(thesekeys, key, 0, validkeys)
          if place>=validkeys or thesekeys[place]>key:
             if place==0: nodekey=None
             else: nodekey=thesekeys[place-1]
          else:
             nodekey = key
          node = node.getnode(nodekey)
       return node.getvalue(key)
          
   def dump(self):
       self.root.dump()
       if self.free!=nilseek:
          free = self.root.clone(self.free)
          free = free.materialize()
          free.dump()
          
   def __del__(self):
       if self.fifo_enabled:
          self.disable_fifo()

class BplusWalker:
   """iterative walker for bplustree leaf nodes."""

   def __init__(self, tree, 
                      keylower=None, includelower=None,
                      keyupper=None, includeupper=None):
       """initialize a walker for tree with key values bounded
          by upper/lower, if given, included or excluded as specified.
          Tree should never be updated while walker is active,
          otherwise behaviour of walker is undefined."""
       self.tree = tree
       self.keylower = keylower
       self.includelower = includelower
       self.keyupper = keyupper
       self.includeupper = includeupper
       if self.tree.getroot() == None:
          self.tree.open()
       # get the first pertinent leaf in tree
       node = self.tree.getroot()
       while node.flag in Interiorflags:
          # interior node, seek a leaf
          if keylower is None:
             nkey = None
          else:
             keys = node.get_keys()
             place = bisect(keys, keylower)
             if place==0: nkey = None
             elif place>len(keys): nkey = keys[-1]
             else: nkey = keys[place-1]
          node = node.getnode(nkey)
       self.node = self.startnode = node
       # preinit
       self.node_index = None
       self.valid = 0 # pessimism
       self.first()

   def first(self):
       """reset walker to first position, or raise IndexError
          if keyrange is empty."""
       node = self.node = self.startnode
       # is the key in the node?
       keys = node.keys
       #print "first at", keys
       keylower = self.keylower
       keyupper = self.keyupper
       validkeys = node.validkeys
       self.valid = 0
       if keylower==None:
          self.node_index = 0
          self.valid = 1
       elif keylower in keys and self.includelower:
          index = self.node_index = keys.index(keylower)
          if index<validkeys:
             self.valid = 1 # hurrah!
       if not self.valid:
          # look for next
          place = bisect(keys, keylower, 0, validkeys)
          if place<validkeys:
             index = self.node_index = place
             testk = keys[index]
             if (testk>keylower or 
                 (self.includelower and testk==keylower)):
                self.valid = 1
             else:
                self.valid = 0
          else:
             # advance to the next node
             next = node.nextneighbor()
             if next is not None:
                self.startnode = next
                self.first()
                return
             else:
                self.valid = 0
       # test keyupper
       if self.valid and keyupper is not None:
          key = self.current_key()
          if key<keyupper or (self.includeupper and key==keyupper):
             self.valid = 1
          else:
             self.valid = 0

   def current_key(self):
       """key the walker currently "points at"."""
       if self.valid: return self.node.keys[self.node_index]
       else: raise IndexError, "not at valid index"

   def current_value(self):
       """value the walker currently "points at"."""
       #print "current at", self.node_index, self.node.indices
       if self.valid: return self.node.indices[self.node_index]
       else: raise IndexError, "not at valid index"

   def next(self):
       """advance to next position, or set to invalid."""
       nextp = self.node_index+1
       node = self.node
       if nextp>=node.validkeys:
          # goto next node
          next = node.nextneighbor()
          if next is None:
             self.valid = 0
             return
          node = self.node = next
          nextp = 0
       #print "next at", node.keys, node.indices, nextp, node.validkeys
       if node.validkeys<=nextp:
          self.valid = 0
       else:
          testkey = node.keys[nextp]
          keyupper = self.keyupper
          if (keyupper is None or
              testkey<keyupper or 
              (self.includeupper and testkey==keyupper)):
             self.node_index = nextp
             self.valid = 1
          else:
             self.valid = 0

class caching_BPT(BplusTree):

   """simple caching.  No updates allowed."""

   def __init__(self, infile, position=None, nodesize=None, keylen=None):
       BplusTree.__init__(self, infile, position, nodesize, keylen)
       self.cache = {}

   def __getitem__(self, key):
       try:
           return self.cache[key]
       except KeyError:
           r = self.cache[key] = BplusTree.__getitem__(self, key)
           return r

   def reset_cache(self):
       self.cache = {}

   def nope(self, *args):
       raise ValueError, "op not permitted for caching_BPT"

   __setitem__ = __delitem__ = nope

class SBplusTree:
   """Wrapper for BPlusTree, maps strings-->strings.
      Key strings are fixed length as in BPlusTree.
      Value strings are arbitrary length but space for
      overwritten or deleted values will be wasted in
      the file (the aren't GC'd, unlike tree nodes which are.
   """

   # can be overridden.
   treeclass = BplusTree
   
   def __init__(self, infile, position=None, nodesize=None, keylen=None):
       self.infile = infile
       self.tree = self.treeclass(infile, position, nodesize, keylen)

   def walker(self, 
                      keylower=None, includelower=None,
                      keyupper=None, includeupper=None):
       return SBplusWalker(self, keylower, includelower,
                                 keyupper, includeupper)

   def __len__(self):
       return len(self.tree)

   def init_params(self):
       return self.tree.init_params()

   def getroot(self):
       return self.tree.getroot()

   def getfile(self):
       return self.infile
       
   def enable_fifo(self, size=33):
       self.tree.enable_fifo(size)
       
   def disable_fifo(self):
       self.tree.disable_fifo()

   def dump(self):
       """ignore real values here, should fix.""" 
       self.tree.dump()

   def startup(self):
       self.tree.startup()

   def open(self):
       self.tree.open()

   def __getitem__(self, key):
       seek = self.tree[key]
       return getstring(self.infile, seek)

   def __setitem__(self, key, value):
       """Warning: overwrite "loses" old value space."""
       #try:
       #   test = self[key]
       #except KeyError:
       #   go = 1
       #else:
       #   go = (test != key)
       #if go:
       # assume overwrite (optimize)
       seek = putstring(self.infile, value)
       self.tree[key] = seek

   def __delitem__(self, key):
       """Warning: loses old value storage."""
       del self.tree[key]

   def has_key(self):
       return self.tree.has_key(self)

class caching_SBPT(SBplusTree):
   """string-->string caching b-plus tree."""
   treeclass = caching_BPT

class SBplusWalker:
   """iterator for string-->string Bplus tree."""

   # can be overridden
   walkerclass = BplusWalker

   def __init__(self, tree,
                      keylower=None, includelower=None,
                      keyupper=None, includeupper=None):
       self.walker = self.walkerclass(tree, keylower, includelower,
                keyupper, includeupper)
       self.file = tree.getfile()
       self.valid = self.walker.valid

   def first(self):
       self.walker.first()
       self.valid = self.walker.valid

   def current_key(self):
       return self.walker.current_key()

   def current_value(self):
       seek = self.walker.current_value()
       return getstring(self.file, seek)

   def next(self):
       self.walker.next()
       self.valid = self.walker.valid

def putstring(infile, s):
       """Add a new string record to eof. return start seek."""
       #save = infile.tell()
       # seek to eof
       infile.seek(0,2)
       last = infile.tell()
       from marshal import dump
       dump(s, infile)
       #infile.seek(save)
       return last

def getstring(infile, i):
       """get an old string record at i"""
       #save = infile.tell()
       infile.seek(i)
       from marshal import load
       s = load(infile)
       #infile.seek(save)
       return s

def recopy_bplus(fromfile, tofile, 
                 treeclass=BplusTree):
    """copy BplusTree from fromfile to tofile.
       from file should be open "rb", tofile "w+b"."""
    fromtree = treeclass(fromfile)
    fromtree.open()
    (f, p, n, k) = fromtree.init_params()
    totree = treeclass(tofile, p, n, k)
    totree.startup()
    return recopy_tree(fromtree, totree)
    
def recopy_tree(fromtree, totree):
    """copy fromtree contents to totree.
       trees must be compatible.
       copy attempts to "compactize" totree."""
    (f,p,n,k) = totree.init_params()
    try:
        totree.enable_fifo()
        walker = fromtree.walker()
        # fill up first node in totree
        part1 = n/2 +1
        part2 = part1-2
        defer = []
        while walker.valid:
           # pseudooptimization: defer n/2-1 tail elements
           # for n even this makes all leaves full (in tests)
           for i in xrange(part1):
               if not walker.valid: break
               totree[ walker.current_key() ] = walker.current_value()
               walker.next()
           for (k,v) in defer:
               totree[k]=v
           defer = []
           for i in xrange(part2):
               if not walker.valid: break
               defer.append( (walker.current_key(), walker.current_value()) )
               walker.next()
        for (k,v) in defer:
            totree[k] = v
        return (fromtree, totree)
    finally:
        #print "disabling fifo"
        totree.disable_fifo()

def recopy_sbplus(fromfile, tofile,
                 treeclass=SBplusTree):
    """copy SBplusTree from fromfile to tofile.
       from file should be open "rb", tofile "w+b".
       this will create a new file without "lost garbage"."""
    return recopy_bplus(fromfile, tofile, treeclass)
    
##### simple dbm compatibility
bignum = 0x7efe77 # 8 million buckets

def myhash(s):
    """portable string hash function.
       (because builtin hash isn't portable)."""
    o = ord
    B = bignum
    result = 775 + len(s)*1001
    for c in s:
        #print result
        result = (result*253 + o(c)*113) % B
    return result

class dbm:
   """dbm compatible index file with unlimited key/value size.
      overwrites, dels and hash collisions leave "junk" in index.
      Alternate implementations left to reader, or to future.
      
      Hash indexed into buckets in an SBplusTree.
      buckets with marshalled dict of {key: value}
      for elements in this bucket.
   """
      
   flagmap = {"r": "rb", "w": "r+b", "c": "w+b"}
   openmodes = ("r", "w")
   treeclass = SBplusTree
   nodesize = 4096
      
   def __init__(self, filename, flag="r", mode=None):
       #print "init", filename, flag, mode
       if mode is not None:
          raise ValueError, "sorry mode not supported (portability)"
       self.fileflag = flag
       rf = self.realflag = self.flagmap[flag]
       self.filename = filename
       f = self.file = open(filename, rf)
       # length record at start of file
       if flag in self.openmodes:
          from marshal import load
          from string import atoi
          self.length = load(f)
          # parameters determined from header
          #print "reopening", self.length, f.tell()
          t = self.tree = self.treeclass(f, f.tell())
          t.open()
       else:
          # put length record
          from marshal import dump
          dump(0, f)
          self.length = 0
          #print "creating", self.length, f.tell()
          t = self.tree = self.treeclass(f, f.tell(), self.nodesize, intsize-1)
          t.startup()
       self.tree.enable_fifo(self.nodesize+3)
          
   closed = 0
          
   def close(self):
       if self.closed: return
       self.tree.disable_fifo()
       # put length record
       if self.length<0: 
          raise ValueError, "negative len?"+`(self.length, self.filename)`
       f = self.file
       if self.fileflag in ("c", "w"):
          f.seek(0)
          from marshal import dump
          dump(self.length, f)
       f.close()
       self.closed = 1
       
   def __del__(self):
       self.close()
       
   def __len__(self):
       return self.length
          
   def hash(self, key):
       from marshal import dumps
       h = myhash(key)
       hs = dumps(h)[1:] # nuke indicator
       return hs
          
   def pairs(self, hash):
       try:
           spairs = self.tree[hash]
       except KeyError:
           return {}
       from marshal import loads
       return loads(spairs)
       
   def setpairs(self, hash, pairs):
       from marshal import dumps
       spairs = dumps(pairs)
       self.tree[hash] = spairs
          
   def __getitem__(self, item):
       h = self.hash(item)
       pairs = self.pairs(h)
       return pairs[item]
   
   def __setitem__(self, item, value):
       h = self.hash(item)
       pairs = self.pairs(h)
       if not pairs.has_key(item):
          self.length = self.length+1
       pairs[item] = value
       self.setpairs(h, pairs)
       #print self.length
   
   def __delitem__(self, item):
       h = self.hash(item)
       pairs = self.pairs(h)
       del pairs[item]
       if pairs:
          self.setpairs(h, pairs)
       else:
          del self.tree[h]
       self.length = self.length-1
       #print self.length
       
   def has_key(self, item):
       try:
           test = self[item]
       except KeyError:
           return 0
       else:
           return 1
   
   def keys(self):
       """not terribly efficient! (should optimize?)"""
       result = []
       w = self.tree.walker()
       from marshal import loads
       while w.valid:
          spairs = w.current_value()
          pairs = loads(spairs)
          for k in pairs.keys():
              result.append(k)
          w.next()
       if len(result)!=self.length:
          raise IndexError, "bad tree length:"+`(len(result), self.length)`
       return result
       
   
   def copy(self, tofilename, flag, mode=None):
       if flag=="r":
          raise ValueError, "nonsense! can't copy into read only index"
       #print "copy", tofilename, flag
       other = dbm(tofilename, flag, mode)
       if flag=="c":
          # create: make optimal
          recopy_tree(self.tree, other.tree)
          other.length = self.length
          other.tree.enable_fifo(other.nodesize+3)
       elif flag=="w":
          # insert-into: simple traversal (collisions waste space)
          w = self.tree.walker()
          from marshal import loads
          while w.valid:
             spairs = w.current_value()
             pairs = loads(spairs)
             for (k,v) in pairs.items():
                 other[k] = v
             w.next()
       return other
       
def testdbm():
    print "creating files test1, 2, 3 for dbm test"
    d1 = dbm("test1", "c")
    for x in range(10):
        key = "hello"*x
        d1[key] = "01234567890"[:-x]
        print key, d1[key]
    print d1.keys()
    for x in range(300):
        d1[oct(x)] = hex(x)
    del d1['']
    print len(d1), d1.keys()
    print "should be 0:", d1.has_key(""), d1.has_key("abd")
    print "copying"
    d2 = d1.copy("test2", "c")
    beforedel = len(d1)
    del d2["hello"]
    print len(d2), d2.keys()
    d2.close()
    d2 = dbm("test2", "r")
    print "should be equal", beforedel-1, len(d2)
    print "keys", d2.keys()
    print "testing copy-into"
    d3 = dbm("test3", "c")
    d3["willy"] = "wally"
    d3.close()
    d3 = d2.copy("test3", "w")
    print "should be equal", beforedel, len(d3)
    print "keys", d3.keys()
    
### test
def test():
    """test program: creates a bplustree file "test".
       try messing with the node size.
    """
    print "creating file 'test' in current directory for test data."
    f = open("test", "w+b")
    B = SBplusTree(f, 0, 1049, 10)
    B.startup()
    B.enable_fifo()
    #return B
    B["this"] = 0xdad
    from string import letters, digits
    for x in letters+digits: B[x] = ord(x)
    for x in "13579finalmopq": del B[x]
    print "final pass"
    from time import time
    s = time()
    for x in range(1000): B[hex(x)] = x; #print x
    print "one thousand assigns", time()-s
    #B.dump()
    B.disable_fifo()
    return (B, f)

def retest():
    from time import time
    f = open("test", "rb")
    B = caching_SBPT(f)
    B.open()
    B.enable_fifo()
    print "retesting"
    for x in "abcdefghi012345":
        try:
             print x, "-->", B[x]
        except KeyError:
             print x, "absent"
    print "entering torture chamber"
    s = time()
    for x in range(1000): l = B[hex(x)]
    print "1 thousand retrieves: ", time()-s
    return B
    print "keys, values between 4 and C (including C)"
    W = SBplusWalker(B, "4", 0, "C", 1)
    while W.valid:
       print (W.current_key(), W.current_value()),
       W.next() 
    print
    print "keys, values between 4 (including 4) and C (excluding C)"
    W = SBplusWalker(B, "4", 1, "C", 0)
    while W.valid:
       print (W.current_key(), W.current_value()),
       W.next()
    print
    print "all keys"
    W = SBplusWalker(B)
    while W.valid:
       print W.current_key(),
       W.next()
    print
    print "A to A inclusive (1 elt)"
    W = SBplusWalker(B, "A", 1, "A", 1)
    while W.valid:
       print W.current_key(),
       W.next()
    print
    print "A to A exclusive (0 elt)"
    W = SBplusWalker(B, "A", 1, "A", 0)
    while W.valid:
       print W.current_key(),
       W.next()
    print
    print "AA to AA inclusive (0 elt)"
    W = SBplusWalker(B, "AA", 1, "AA", 0)
    while W.valid:
       print W.current_key(),
       W.next()
    print
    print
    B.disable_fifo()
    return (W, B, f)

if __name__=="__main__":
   #testdbm()
   (B,f) = test()
   B=None
   f.close()
   #retest()
