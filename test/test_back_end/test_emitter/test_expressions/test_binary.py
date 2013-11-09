__author__ = 'samyvilar'

from test.test_back_end.test_emitter.test_statements.test_compound import TestStatements


class TestCompoundAssignment(TestStatements):
    def test_compound_addition(self):
        code = """
        {
            int a = 10, b = 1;
            a += b;
        }
        """
        self.evaluate(code)
        self.assertEqual(self.mem[self.cpu.stack_pointer], 11)


class TestPointerArithmetic(TestStatements):
    def test_pointer_subtraction(self):
        code = """
        {
            unsigned int size = -1;
            struct foo {double a; int b[10];} *a = (void *)sizeof(struct foo);
            size = a - 1;
        }
        """
        self.evaluate(code)
        self.assertEqual(self.mem[self.cpu.stack_pointer], 0)

    def test_pointer_pointer_subtraction(self):
        code = """
        {
            unsigned int index = 0;
            struct foo {double a; int b[10];}
                *a = (void *)0,
                *b = (void *)sizeof(struct foo);
            index = b - a;
        }
        """
        self.evaluate(code)
        self.assertEqual(self.mem[self.cpu.stack_pointer], 1)

    def test_pointer_addition(self):
        code = """
        {
            unsigned int offset = -1;
            struct foo {double a; int b[10];};
            struct foo *a = (void *)0;
            a++;
            offset = (unsigned long long)a - sizeof(struct foo);
        }
        """
        self.evaluate(code)
        self.assertEqual(self.mem[self.cpu.stack_pointer], 0)