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
Grab the Medium Level IL for each cross reference

```
xref.medium_level_il
```

Why Medium Level IL? More dataflow analysis is available than assembly or Low Level IL

---
## Filter xrefs
Ignore format strings with %s corresponding to a constant string (since we can't control it)

---
```python
for sprintf in sprintfs:
    format_str = string_from_addr(bv, sprintf.params[1].constant).replace('\n', '')
    if '%s' not in format_str:
        continue
```

@[1](For each sprintf cross reference)
@[2](Grab the format string constant from the binary: 0x40095c -> /tmp/%s_%d)
@[3-4](Ignore any format strings that don't contain %s)

---
## Find constant %s 
Filter xrefs with constant %s

```
sprintf(result, "SUCCESS: %s\n", "Log file created.");
```

---
## Easy cases.. Extend for more robust matching

```python
m = re.findall('%[^%]', format_str)
for fmt, param in zip(m, sprintf.params[2:]):
    print(format_str, fmt, param.operation)
```

```
('/tmp/%s_%d', '%s', <MLIL_VAR_SSA: 80>)
('/tmp/%s_%d', '%d', <MLIL_VAR_SSA: 80>)
('SUCCESS: %s', '%s', <MLIL_CONST: 12>)
```

---
```python
m = re.findall('%[^%]', format_str)
for fmt, param in zip(m, sprintf.params[2:]):
    if fmt == '%s' and param.operation == MLIL_CONST:
        continue
```
@[3-4](Add the check to ignore constant string parameters)

---
### What do we currently have?

```c
sprintf(path, "/tmp/%s_%d", buf, strlen(buf));
```

```
(<il: mem#8 = 0x400650(rdi_1#3, 0x40095c, rdx_1#3, rcx_1#1) @ mem#7>, 
	'%s', <stack frame offset -0x118>)
(<il: mem#8 = 0x400650(rdi_1#3, 0x40095c, rdx_1#3, rcx_1#1) @ mem#7>, 
	'%d', <undetermined>)
```


```
# Found a stack offset variable. Find where it might have been set
if fmt == '%s' and param.value.type == RegisterValueType.StackFrameOffset:
    new_format_str = new_format_str.replace(fmt, str(param.value))
```
