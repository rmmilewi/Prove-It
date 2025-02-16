from proveit import Literal, Operation, ExprList, ProofFailure, maybeFencedString, USE_DEFAULTS
from proveit.logic import Membership
import proveit._common_
from proveit._common_ import S, x

class Exp(Operation):
    # operator of the Exp operation.
    _operator_ = Literal(stringFormat='Exp', context=__file__)    
    
    def __init__(self, base, exponent):
        r'''
        Raise base to exponent power.
        '''
        Operation.__init__(self, Exp._operator_, (base, exponent))
        self.base = base
        self.exponent = exponent

    def membershipObject(self, element):
        return ExpSetMembership(element, self)
    
    def _closureTheorem(self, numberSet):
        import natural.theorems
        import real.theorems
        import complex.theorems
        from proveit.number import two
        if numberSet == NaturalsPos:
            return natural.theorems.powClosure
        elif numberSet == Reals:
            return real.theorems.powClosure
        elif numberSet == RealsPos:
            if self.exponent != two: # otherwise, use deduceInRealsPosDirectly(..)
                return real.theorems.powPosClosure            
        elif numberSet == Complexes:
            return complex.theorems.powClosure
    
    def simplification(self, assumptions=frozenset()):
        '''
        For trivial cases, a zero or one exponent or zero or one base,
        derive and return this exponential expression equated with a simplified form.
        Assumptions may be necessary to deduce necessary conditions for the simplification.
        '''
        from .theorems import expZeroEqOne, exponentiatedZero, exponentiatedOne
        from .theorems import expOne
        if self.exponent == zero:
            deduceInComplexes(self.base, assumptions)
            deduceNotZero(self.base, assumptions)
            return expZeroEqOne.specialize({a:self.base})
        elif self.exponent == one:
            return expOne.specialize({a:self.base})
        elif self.base == zero:
            deduceInComplexes(self.exponent, assumptions)
            deduceNotZero(self.exponent, assumptions)
            return exponentiatedZero.specialize({x:self.exponent})
        elif self.base == one:
            deduceInComplexes(self.exponent, assumptions)
            return exponentiatedOne.specialize({x:self.exponent})
        else:
            raise ValueError('Only trivial simplification is implemented (zero or one for the base or exponent)')

    def simplified(self, assumptions=frozenset()):
        '''
        For trivial cases, a zero or one exponent or zero or one base,
        derive this exponential expression equated with a simplified form
        and return the simplified form.
        Assumptions may be necessary to deduce necessary conditions for the simplification.
        '''
        return self.simplification(assumptions).rhs
        
    def deduceInRealsPosDirectly(self, assumptions=frozenset()):
        import real.theorems
        from number import two
        if self.exponent == two:
            deduceInReals(self.base, assumptions)
            deduceNotZero(self.base, assumptions)
            return real.theorems.sqrdClosure.specialize({a:self.base}).checked(assumptions)
        # only treating certain special case(s) in this manner
        raise DeduceInNumberSetException(self, RealsPos, assumptions)

    def _notEqZeroTheorem(self):
        import complex.theorems
        return complex.theorems.powNotEqZero

    def string(self, **kwargs):
        return self.formatted('string', **kwargs)

    def latex(self, **kwargs):
        return self.formatted('latex', **kwargs)
            
    def formatted(self, formatType, **kwargs):
        inner_str = self.base.formatted(formatType, forceFence=True)+r'^{'+self.exponent.formatted(formatType, fence=False) + '}'
        # only fence if forceFence=True (nested exponents is an example of when fencing must be forced)
        kwargs['fence'] = kwargs['forceFence'] if 'forceFence' in kwargs else False        
        return maybeFencedString(inner_str, **kwargs)
    
    def distributeExponent(self, assumptions=frozenset()):
        from proveit.number import Fraction
        from proveit.number.division.theorems import fracIntExpRev, fracNatPosExpRev
        if isinstance(self.base, Fraction):
            exponent = self.exponent
            try:
                deduceInNaturalsPos(exponent, assumptions)
                deduceInComplexes([self.base.numerator, self.base.denominator], assumptions)
                deduceNotZero(self.base.denominator, assumptions)
                return fracNatPosExpRev.specialize({n:exponent}).specialize({a:self.numerator.base, b:self.denominator.base})
            except:
                deduceInIntegers(exponent, assumptions)
                deduceInComplexes([self.base.numerator, self.base.denominator], assumptions)
                deduceNotZero(self.base.numerator, assumptions)
                deduceNotZero(self.base.denominator, assumptions)
                return fracIntExpRev.specialize({n:exponent}).specialize({a:self.base.numerator, b:self.base.denominator})
        raise Exception('distributeExponent currently only implemented for a fraction base')
        
    def raiseExpFactor(self, expFactor, assumptions=frozenset()):
        from proveit.number import Neg
        from .theorems import intExpOfExp, intExpOfNegExp
        if isinstance(self.exponent, Neg):
            b_times_c = self.exponent.operand
            thm = intExpOfNegExp
        else:
            b_times_c = self.exponent
            thm = intExpOfExp
        if not hasattr(b_times_c, 'factor'):
            raise Exception('Exponent not factorable, may not raise the exponent factor.')
        factorEq = b_times_c.factor(expFactor, pull='right', groupRemainder=True, assumptions=assumptions)
        if factorEq.lhs != factorEq.rhs:
            # factor the exponent first, then raise this exponent factor
            factoredExpEq = factorEq.substitution(self)
            return factoredExpEq.applyTransitivity(factoredExpEq.rhs.raiseExpFactor(expFactor, assumptions=assumptions))
        nSub = b_times_c.operands[1]
        aSub = self.base
        bSub = b_times_c.operands[0]
        deduceNotZero(aSub, assumptions)
        deduceInIntegers(nSub, assumptions)
        deduceInComplexes([aSub, bSub], assumptions)
        return thm.specialize({n:nSub}).specialize({a:aSub, b:bSub}).deriveReversed()

    def lowerOuterExp(self, assumptions=frozenset()):
        from proveit.number import Neg
        from .theorems import intExpOfExp, intExpOfNegExp, negIntExpOfExp, negIntExpOfNegExp
        if not isinstance(self.base, Exp):
            raise Exception('May only apply lowerOuterExp to nested Exp operations')
        if isinstance(self.base.exponent, Neg) and isinstance(self.exponent, Neg):
            b_, n_ = self.base.exponent.operand, self.exponent.operand
            thm = negIntExpOfNegExp
        elif isinstance(self.base.exponent, Neg):
            b_, n_ = self.base.exponent.operand, self.exponent
            thm = intExpOfNegExp
        elif isinstance(self.exponent, Neg):
            b_, n_ = self.base.exponent, self.exponent.operand
            thm = negIntExpOfExp
        else:
            b_, n_ = self.base.exponent, self.exponent
            thm = intExpOfExp
        a_ = self.base.base
        deduceNotZero(self.base.base, assumptions)
        deduceInIntegers(n_, assumptions)
        deduceInComplexes([a_, b_], assumptions)
        return thm.specialize({n:n_}).specialize({a:a_, b:b_})
    
class ExpSetMembership(Membership):
    '''
    Defines methods that apply to membership in an exponentiated set. 
    '''
    
    def __init__(self, element, domain):
        Membership.__init__(self, element)
        self.domain = domain

    def conclude(self, assumptions=USE_DEFAULTS):
        '''
        Attempt to conclude that the element is in the exponentiated set.
        '''   
        from proveit.logic import InSet
        from proveit.logic.set_theory.membership._theorems_ import exp_set_0, exp_set_1, exp_set_2, exp_set_3, exp_set_4, exp_set_5, exp_set_6, exp_set_7, exp_set_8, exp_set_9
        from proveit.number import zero, isLiteralInt, DIGITS
        element = self.element
        domain = self.domain
        elem_in_set = InSet(element, domain)
        if not isinstance(element, ExprList):
            raise ProofFailure(elem_in_set, assumptions, "Can only automatically deduce membership in exponentiated sets for an element that is a list")
        exponent_eval = domain.exponent.evaluation(assumptions=assumptions)
        exponent = exponent_eval.rhs
        base = domain.base
        #print(exponent, base, exponent.asInt(),element, domain, len(element))
        if isLiteralInt(exponent):
            if exponent == zero:
                return exp_set_0.specialize({x:element, S:base}, assumptions=assumptions)
            if len(element) != exponent.asInt():
                raise ProofFailure(elem_in_set, assumptions, "Element not a member of the exponentiated set; incorrect list length")
            elif exponent in DIGITS:
                # thm = forall_S forall_{a, b... in S} (a, b, ...) in S^n
                thm = locals()['exp_set_%d'%exponent.asInt()]
                expr_map = {S:base} # S is the base
                # map a, b, ... to the elements of element.
                expr_map.update({proveit._common_.__getattr__(chr(ord('a')+k)):elem_k for k, elem_k in enumerate(element)})
                elem_in_set = thm.specialize(expr_map, assumptions=assumptions)
            else:
                raise ProofFailure(elem_in_set, assumptions, "Automatic deduction of membership in exponentiated sets is not supported beyond an exponent of 9")
        else:
            raise ProofFailure(elem_in_set, assumptions, "Automatic deduction of membership in exponentiated sets is only supported for an exponent that is a literal integer")
        if exponent_eval.lhs != exponent_eval.rhs:
            # after proving that the element is in the set taken to the evaluation of the exponent,
            # substitute back in the original exponent.
            return exponent_eval.subLeftSideInto(elem_in_set, assumptions=assumptions)
        return elem_in_set

    def sideEffects(self, knownTruth):
        return
        yield
