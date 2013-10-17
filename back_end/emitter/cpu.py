__author__ = 'samyvilar'

import sys

from itertools import izip, repeat, chain
from collections import defaultdict

from logging_config import logging
from front_end.loader.locations import loc
from back_end.virtual_machine.instructions.architecture import no_operand_instr_ids, wide_instr_ids
from back_end.virtual_machine.instructions.architecture import Push, Pop, Halt, Pass, Jump
from back_end.virtual_machine.instructions.architecture import Add, Subtract, Multiply, Divide, Mod
from back_end.virtual_machine.instructions.architecture import AddFloat, SubtractFloat, MultiplyFloat, DivideFloat
from back_end.virtual_machine.instructions.architecture import And, Or, Xor, Not, ShiftLeft, ShiftRight
from back_end.virtual_machine.instructions.architecture import ConvertToInteger, ConvertToFloat
from back_end.virtual_machine.instructions.architecture import LoadZeroFlag, LoadMostSignificantBit, LoadCarryBorrowFlag
from back_end.virtual_machine.instructions.architecture import AbsoluteJump, LoadInstructionPointer
from back_end.virtual_machine.instructions.architecture import RelativeJump, JumpTrue, JumpFalse, JumpTable
from back_end.virtual_machine.instructions.architecture import LoadBaseStackPointer, LoadStackPointer, Load, Set
from back_end.virtual_machine.instructions.architecture import SetBaseStackPointer, SetStackPointer, SystemCall, operns
from back_end.virtual_machine.instructions.architecture import Allocate, Dup, Swap, PushFrame, PopFrame


logger = logging.getLogger('virtual_machine')


def pop(cpu, mem):
    cpu.stack_pointer += 1
    return mem[cpu.stack_pointer]


def push(value, cpu, mem):
    assert isinstance(value, (int, float, long))
    mem[cpu.stack_pointer] = value
    cpu.stack_pointer -= 1


def add(oper1, oper2):
    return oper1 + oper2


def sub(oper1, oper2):
    return oper1 - oper2


def mult(oper1, oper2):
    return oper1 * oper2


def div(oper1, oper2):
    return oper1 / oper2


def _and(oper1, oper2):
    return oper1 & oper2


def _or(oper1, oper2):
    return oper1 | oper2


def _xor(oper1, oper2):
    return oper1 ^ oper2


def mod(oper1, oper2):
    return oper1 % oper2


def _shift_left(oper1, oper2):
    return oper1 << (oper2 & 0b111111)


def _shift_right(oper1, oper2):
    return oper1 >> oper2


def _not(oper1):
    return ~oper1


def convert_to_int(oper1):
    return long(oper1)


def convert_to_float(oper1):
    return float(oper1)


def bin_arithmetic(instr, cpu, mem):
    oper2, oper1 = pop(cpu, mem), pop(cpu, mem)
     # make sure emitter doesn't generate instr that mixes types.
    # if not (isinstance(oper1, (int, long)) and isinstance(oper2, (int, long)) or
    #         isinstance(oper1, float) and isinstance(oper2, float)):
    #     raise ValueError('Bad operands!')
    result = bin_arithmetic.rules[type(instr)](oper1, oper2)
    if isinstance(instr, (Add, AddFloat, Subtract, SubtractFloat, Multiply, MultiplyFloat, Divide, DivideFloat)):
        cpu.most_significant_bit_flag = cpu.carry_borrow_flag = int(result < 0)
        cpu.zero_flag = int(not result)
    return result
bin_arithmetic.rules = {
    Add: add,
    AddFloat: add,
    Subtract: sub,
    SubtractFloat: sub,
    Multiply: mult,
    MultiplyFloat: mult,
    Divide: div,
    DivideFloat: div,
    And: _and,
    Or: _or,
    Xor: _xor,
    Mod: mod,
    ShiftLeft: _shift_left,
    ShiftRight: _shift_right,
}


def unary_arithmetic(instr, cpu, mem):
    return unary_arithmetic.rules[type(instr)](pop(cpu, mem))
unary_arithmetic.rules = {
    Not: _not,
    ConvertToFloat: convert_to_float,
    ConvertToInteger: convert_to_int,
}


def expr(instr, cpu, mem, _):
    push(expr.rules[type(instr)](instr, cpu, mem), cpu, mem)
expr.rules = {rule: bin_arithmetic for rule in bin_arithmetic.rules}
expr.rules.update(izip(unary_arithmetic.rules, repeat(unary_arithmetic)))


def _jump(addr, cpu, *_):
    cpu.instr_pointer = addr


def abs_jump(instr, cpu, mem):
    _jump(pop(cpu, mem), cpu, mem)


def rel_jump(instr, cpu, mem):
    _jump(cpu.instr_pointer + operns(instr)[0] + instr_size(instr), cpu, mem)


def jump_if_true(instr, cpu, mem):
    _jump(cpu.instr_pointer + ((operns(instr)[0] + instr_size(instr)) if pop(cpu, mem) else instr_size(instr)), cpu, mem)


def jump_if_false(instr, cpu, mem):
    _jump(cpu.instr_pointer + ((operns(instr)[0] + instr_size(instr)) if not pop(cpu, mem) else instr_size(instr)), cpu, mem)


def jump_table(instr, cpu, mem):
    _jump(cpu.instr_pointer + instr.cases.get(pop(cpu, mem), instr.cases['default']) + 2, cpu, mem)


def jump(instr, cpu, mem, _):
    jump.rules[type(instr)](instr, cpu, mem)
jump.rules = {
    RelativeJump: rel_jump,
    AbsoluteJump: abs_jump,
    JumpTrue: jump_if_true,
    JumpFalse: jump_if_false,
    JumpTable: jump_table,
}


def _pass(instr, cpu, *_):
    pass


def load_base_pointer(instr, cpu, mem, _):
    push(cpu.base_pointer, cpu, mem)


def set_base_pointer(instr, cpu, mem, _):
    cpu.base_pointer = _pop(instr, cpu, mem, _)


def load_stack_pointer(instr, cpu, mem, _):
    push(cpu.stack_pointer, cpu, mem)


def set_stack_pointer(instr, cpu, mem, _):
    cpu.stack_pointer = pop(cpu, mem)


def load_instr_pointer(instr, cpu, mem, _):
    push(cpu.instr_pointer + instr_size(instr), cpu, mem)


def _allocate(instr, cpu, mem, _):
    cpu.stack_pointer += operns(instr)[0]


def _dup(instr, cpu, mem, _):
    for addr in xrange(cpu.stack_pointer + operns(instr)[0], cpu.stack_pointer, -1):
        push(mem[addr], cpu, mem)


def _swap(instr, cpu, mem, _):
    amount = operns(instr)[0]
    for addr in xrange(cpu.stack_pointer + operns(instr)[0], cpu.stack_pointer, -1):
        temp = mem[addr]
        mem[addr] = mem[addr + amount]
        mem[addr + amount] = temp


def _load(instr, cpu, mem, _):
    addr, quantity = pop(cpu, mem), operns(instr)[0]
    for index in reversed(xrange(addr, addr + quantity)):
        push(mem[index], cpu, mem)


def _set(instr, cpu, mem, os):
    addr, quantity, stack_pointer = _pop(instr, cpu, mem, os), operns(instr)[0], cpu.stack_pointer + 1
    for addr, stack_addr in izip(xrange(addr, addr + quantity), xrange(stack_pointer, stack_pointer + quantity)):
        mem[addr] = mem[stack_addr]


def _push(instr, cpu, mem, _):
    push(operns(instr)[0], cpu, mem)


def _pop(instr, cpu, mem, _):
    return pop(cpu, mem)


def _push_frame(instr, cpu, mem, _):
    cpu.frames.append((cpu.base_pointer, cpu.stack_pointer))


def _pop_frame(instr, cpu, mem, _):
    cpu.base_pointer, cpu.stack_pointer = cpu.frames.pop()


def system_call(instr, cpu, mem, os):
    os.calls[pop(cpu, mem)](cpu, mem, os)


def instr_size(instr):
    return instr_size.rules[type(instr)]
instr_size.rules = {instr: 1 for instr in no_operand_instr_ids}  # default all instructions to 1
instr_size.rules.update((instr, 2) for instr in wide_instr_ids)  # wide instructions are 2
instr_size.rules[JumpTable] = 2


def instr_pointer_update(instr):
    return instr_pointer_update.rules[type(instr)]
instr_pointer_update.rules = {JumpTable: 0}  # JumpTable is a variable length instruction ...
for instr in instr_size.rules:  # Make sure not to update the instruction pointer on Jump instructions ...
    instr_pointer_update.rules[instr] = 0 if issubclass(instr, Jump) else instr_size.rules[instr]


def evaluate(cpu, mem, os=None):
    os = os or Kernel()
    instr = None

    while not isinstance(instr, Halt):
        instr = mem[cpu.instr_pointer]
        evaluate.rules[type(instr)](instr, cpu, mem, os)
        cpu.instr_pointer += instr_pointer_update(instr)
evaluate.rules = {
    Halt: _pass,  # evaluate will halt ...
    Pass: _pass,
    Push: _push,
    Pop: _pop,

    LoadZeroFlag: lambda instr, cpu, mem, _: push(cpu.zero_flag, cpu, mem),
    LoadCarryBorrowFlag: lambda instr, cpu, mem, _: push(cpu.carry_borrow_flag, cpu, mem),
    LoadMostSignificantBit: lambda instr, cpu, mem, _: push(cpu.most_significant_bit_flag, cpu, mem),

    LoadBaseStackPointer: load_base_pointer,
    SetBaseStackPointer: set_base_pointer,
    LoadStackPointer: load_stack_pointer,
    SetStackPointer: set_stack_pointer,

    LoadInstructionPointer: load_instr_pointer,

    Allocate: _allocate,
    Dup: _dup,
    Swap: _swap,

    PushFrame: _push_frame,
    PopFrame: _pop_frame,

    Load: _load,
    Set: _set,
    SystemCall: system_call,
}
evaluate.rules.update(chain(izip(expr.rules, repeat(expr)), izip(jump.rules, repeat(jump))))

stdin_file_no = getattr(sys.stdin, 'fileno', lambda: 0)()
stdout_file_no = getattr(sys.stdout, 'fileno', lambda: 1)()
stderr_file_no = getattr(sys.stderr, 'fileno', lambda: 2)()
std_files = {stdin_file_no: sys.stdin, stdout_file_no: sys.stdout, stderr_file_no: sys.stderr}


class Kernel(object):
    def __init__(self, calls=None):
        self.opened_files = std_files
        self.calls = calls or {}


class CPU(object):
    def __init__(self):
        self.instr_pointer = 0
        self.zero_flag, self.carry_borrow_flag, self.most_significant_bit_flag = 0, 0, 0
        self._stack_pointer, self.base_pointer = -1, -1
        self.frames = []

    @property
    def stack_pointer(self):
        return self._stack_pointer

    @stack_pointer.setter
    def stack_pointer(self, value):
        self._stack_pointer = value


class VirtualMemory(defaultdict):
    def __init__(self, default_factory=long):
        super(VirtualMemory, self).__init__(default_factory)

try:
    from back_end.virtual_machine.c.cpu import c_evaluate as evaluate, CPU, VirtualMemory, Kernel
except ImportError as er:
    print 'Failed to import C implementations, reverting to Python'