@title[Intro]
## Pattern matching bugs with binja
---

## Core idea
Not to positively identify all bugs, but guide the analyst to certain parts of the code that might contain bugs

---

```c
printf("Enter log file\n");
read(0, buf, 0x100);
path = malloc(100);
sprintf(path, "/tmp/%s_%d", buf, strlen(buf));
sprintf(result, "SUCCESS: %s\n", "Log file created.");
```

@[4](sprintf with _%s_ using buf into path)
@[2](buf comes from a read)
@[3](path comes from a malloc of 100)
@[2-4](Buffer overflow of 0x100+some in buffer of 100)

---
## Bug class

sprintf with a `%s` format string that is a non-constant parameter

---
```python
# Create Binary View to access all operations
file = sys.argv[1]
bv = BinaryViewType.get_view_of_file(file)

# Get all cross references to `sprintf` calls
sprintf_addr = bv.symbols['sprintf'].address
sprintf_xrefs = bv.get_code_refs(sprintf_addr)
```
@[1-3](Get core Binary View object)
@[4-7](Get all cross references for sprintf)

---
```python
>>> print(sprintf_xrefs)
[<ref: x86_64@0x400808>, 
 <ref: x86_64@0x400826>, 
 <ref: x86_64@0x400847>]
```

---
Each cross reference contains the following attributes

```
>>> print(vars(sprintf_refs[0]))
{'function': <func: x86_64@0x400766>, 
 'arch': <arch: x86_64>, 
 'address': 4196360L}
```

We care about the **function** and the **address**

---
## Goal
Retrieve the MLIL instruction associated with each xref

```
xref.function.get_low_level_il_at(xref.address).medium_level_il
```
OR **with a certain someone's pull request**
```
xref.medium_level_il
```

+++
@[58](List comprehension to go from xref -> MLILSSA)

We'll get to why Medium Level IL SSA form later

---
## Filter xrefs
Where %s corresponds to a constant string (since we can't control it)

@[64]

`.params` gives parameter variables for a called function

```
0x40095c -> /tmp/%s_%d
```

+++
@[65-66](Ignore all format strings without a %s)

---
## Find constant %s 
@[71-77]()
