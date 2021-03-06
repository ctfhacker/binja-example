@title[Intro]
## Pattern matching bugs with binja
---

## Core idea
Guide the reverser to certain parts of code that might contain bugs using existing bug patterns

---

```c
printf("Enter log file\n");
read(0, buf, 0x100);
path = malloc(100);
sprintf(path, "/tmp/%s_%d", buf, strlen(buf));
sprintf(result, "SUCCESS: %s\n", "Log file created.");
```

@[2](buf comes from a read)
@[3](path comes from a malloc of 100)
@[4](sprintf with _%s_ using buf into path)
@[2-4](Buffer overflow of 0x100+some in buffer of 100)

---
## Bug class

sprintf with a `%s` format string that is a non-constant parameter

---
Catch - Dynamic %s

```c
sprintf(path, "/tmp/%s_%d", buf, strlen(buf));
```

Ignore - Constant %s

```c
sprintf(result, "SUCCESS: %s\n", "Log file created.");
```

---

## Algorithm?

* Find calls to sprintf
* If the format string for sprintf doesn't contain %s, ignore it
* If the parameter associated with %s is constant, ignore it
* Slice (dafaq?) backwards on each found parameter to find where it was used

---

## Slice? Quewha?

---

![Before](./before_ssa.png)

---
![After](./after_ssa1.png)

SSA guarentees that each individual variable is assigned to only once

---
## Result?

```
sprintf("/tmp/%s_%d", X, Y)
X - var_118
    read(0, var_118, 0x100)
    strlen(var_118)
```

---

Binary Ninja

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
 <ref: x86_64@0x400826>]
```

---
Grab the Medium Level IL for each cross reference

```
xref.medium_level_il.ssa_form
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

![ssa1](./after_ssa1.png)

---
## Find constant %s 
Filter xrefs with constant %s

```
sprintf(result, "SUCCESS: %s\n", "Log file created.");
```

---
## Format strings

Align format strings with their parameters

```python
m = re.findall('%[^%]', format_str)
for fmt, param in zip(m, sprintf.params[2:]):
    print(format_str, fmt, param.operation)
```

`sprintf.params` attribute will give the parameters to a function call

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

---

The parameters for this sprintf

```
param.value
```

```json
('%s', <stack frame offset -0x118>)
('%d', <undetermined>)
```

---
Grab location of where the stack variable was assigned


```python
s_param = sprintf.params[2].src
<ssa <var void* rdx_1> version 3>

definition_index = curr_func.get_ssa_var_definition(s_param) 
curr_ins = curr_func[definition_index]
```

@[1-2](s_param is the SSA variable for the %s parameter)
@[4](Grab instruction index for the definition - definition_index = 22)
@[5](Extract the instruction at the retrieved index)

![ssa2](./after_ssa1.png)

---
Stack Variables aren't "assigned to" (per ssa)

Loop through all instrutions looking for uses of the same stack variable above the current instruction

![Want to find](variables.png)

---
```python
# Pseudocode
for il in func.instrutions:
    if il.operation != MediumLevelILOperation.MLIL_SET_VAR \
        or il.src.src != wanted_variable:
        continue

    dest_var = il.dest
    uses = [x for x in curr_func.get_ssa_var_uses(dest_var) \
            if x < sprintf_index]
```

@[1-2](Loop through all instructions in the current function)
@[3-4](Ignore any instruction that doesn't involve our found stack variable)
@[6-9](Grab all of the uses and retrieve their corresponding instructions )

![ssa](./after_ssa3.png)

---
```json
[0x40081e] sprintf(dest, /tmp/<stack frame offset -0x118>_%d)
    --------------------
    rsi_1#2 = &var_118
    mem#5 = read(0, rsi_1#2, 0x100) @ mem#3
    --------------------
    rdi#2 = &var_118
    rax_3#4, mem#7 = strlen(rdi#1) @ mem#6
    --------------------
    TODO: Write dest variable slice
```

@[1](var_118 is used in the sprintf)
@[2-4](var_118 was used in a read)
@[6-8](var_118 was used in a strlen)
