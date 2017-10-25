import sys
sys.path.append('/home/ctfhacker/binaryninja/python')
from binaryninja import *
import re

def find_stack_var_uses(curr_func, var, instr_index):
    definition_index = curr_func.get_ssa_var_definition(param.src) 
    curr_ins = curr_func[definition_index]

    if curr_ins.src.src.source_type != VariableSourceType.StackVariableSourceType:
        return

    curr_var = curr_ins.src.src
    result = []
    for bb in curr_func:
        for il in bb:
            if il.operation != MediumLevelILOperation.MLIL_SET_VAR_SSA:
                continue
            if il.src.operation != MediumLevelILOperation.MLIL_ADDRESS_OF:
                continue
            if il.src.src == curr_var:
                dst_var = il.dest
                uses = [curr_func[x] for x in curr_func.get_ssa_var_uses(dst_var) if x < instr_index]
                for use in uses:
                    if use.operation != MediumLevelILOperation.MLIL_CALL_SSA:
                        continue

                    # Get function symbol corresponding to the called function
                    func_addr = use.operands[1].constant
                    func_name = [k for k,v in bv.symbols.iteritems() if v.address == func_addr][0]

                    hex_func_addr = '0x{:x}'.format(use.operands[1].constant)
                    func_call = str(use).replace(hex_func_addr, func_name)
                    result.append((il, func_call))
    return result

def string_from_addr(bv, addr):
    if not isinstance(addr, int) and not isinstance(addr, long):
        addr = addr.constant

    try:
        string = [x for x in bv.get_strings() if x.start == addr][0]
    except IndexError:
        return ''

    return bv.read(string.start, string.length)


# Create Binary View to access all operations
file = sys.argv[1]
bv = BinaryViewType.get_view_of_file(file)

# Get all cross references to `sprintf` calls
sprintf_addr = bv.symbols['sprintf'].address
sprintf_xrefs = bv.get_code_refs(sprintf_addr)

# Get all MLILSSA instructions for cross references
sprintfs = [xref.function.get_low_level_il_at(xref.address).medium_level_il.ssa_form for xref in sprintf_xrefs]
for sprintf in sprintfs:
    print(sprintf.params[1])
    print(string_from_addr(bv, sprintf.params[1].constant))

for sprintf in sprintfs:
    format_str = string_from_addr(bv, sprintf.params[1].constant).replace('\n', '')
    if '%s' not in format_str:
        continue
    
    params = []
    new_format_str = format_str

    # Easy cases.. Extend for more robust matching
    m = re.findall('%[^%]', format_str)
    for fmt, param in zip(m, sprintf.params[2:]):
        if fmt == '%s' and param.operation == MediumLevelILOperation.MLIL_CONST:
            # param = string_from_addr(bv, param.constant)
            # new_format_str = new_format_str.replace(fmt, param)
            continue

        curr_func = param.function
        index = new_format_str.find(fmt)
        
        print(sprintf, fmt, param.value)
        # Found a stack offset variable. Find where it might have been set
        if fmt == '%s' and param.value.type == RegisterValueType.StackFrameOffset:
            new_format_str = new_format_str.replace(fmt, str(param.value))
            print('[0x{:x}] sprintf({})'.format(sprintf.address, new_format_str))

            uses = find_stack_var_uses(curr_func, param.src, sprintf.instr_index)
            for use in uses:
                print('    ' + '-' * 20)
                for x in use:
                    print('    {}'.format(x))

            print('    ' + '-' * 20)
            """
        else:
            new_format_str = new_format_str.replace(fmt, str(param.value))
