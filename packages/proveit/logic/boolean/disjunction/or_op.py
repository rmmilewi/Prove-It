from proveit import Literal, Operation, USE_DEFAULTS, ProofFailure
from proveit._common_ import A, B, C, D, AA, BB, CC, DD, EE, i,j,k,l, m, n
from proveit.logic.boolean.booleans import inBool

class Or(Operation):
    # The operator of the Or operation
    _operator_ = Literal(stringFormat='or', latexFormat=r'\lor', context=__file__)

    trivialDisjunctions = set() #used to avoid infinite recursion inside of deduceUnaryEquiv

    def __init__(self, *operands):
        '''
        Or together any number of operands: A or B or C
        '''
        Operation.__init__(self, Or._operator_, operands)
        #deduce trivial disjunctive equivalances with 0 or 1 operand
        #avoid infinite recursion by storing previously encountered expressions
        if self in Or.trivialDisjunctions:
            return
        if len(operands) == 0:
            Or.trivialDisjunctions.add(self)
            try:
                from proveit.logic.boolean.disjunction._axioms_ import emptyDisjunction
            except:
                pass # emptyDisjunction not initially defined when doing a clean rebuild
        if len(operands) == 1:
            operand = operands[0]
            try: 
                Or.trivialDisjunctions.add(self)
                inBool(operand).prove(automation = False)
                self.deduceUnaryEquiv()
            except:
                pass

    def conclude(self, assumptions=USE_DEFAULTS):
        '''
        Try to automatically conclude this disjunction.  If any of its
        operands have pre-existing proofs, it will be proven via the orIfAny
        theorem.  Otherwise, a reduction proof will be attempted 
        (evaluating the operands).
        '''
        from ._theorems_ import trueOrTrue, trueOrFalse, falseOrTrue
        if self in {trueOrTrue.expr, trueOrFalse.expr, falseOrTrue.expr}:
            # should be proven via one of the imported theorems as a simple special case
            return self.prove() 
        # Prove that the disjunction is true by proving that ANY of its operands is true.
        # In the first attempt, don't use automation to prove any of the operands so that
        # we don't waste time trying to prove operands when we already know one to be true
        for useAutomationForOperand in [False, True]:
            provenOperandIndices = []
            for k, operand in enumerate(self.operands):
                try:
                    operand.prove(assumptions, automation=useAutomationForOperand)
                    provenOperandIndices.append(k)
                    self.concludeViaExample(operand, assumptions=assumptions) # possible way to prove it
                except ProofFailure:
                    pass
            if len(self.operands) == 2 and len(provenOperandIndices) > 0:
                # One or both of the two operands were known to be true (without automation).
                # Try a possibly simpler proof than concludeViaExample. 
                try:
                    if len(provenOperandIndices)==2:
                        return self.concludeViaBoth(assumptions)
                    elif provenOperandIndices[0] == 0:
                        return self.concludeViaOnlyLeft(assumptions)
                    else:
                        return self.concludeViaOnlyRight(assumptions)
                except:
                    pass
            if len(provenOperandIndices) > 0:
                try:
                    # proven using concludeViaExample above (unless orIf[Any,Left,Right] was not a usable theorem,
                    # in which case this will fail and we can simply try the default below)
                    return self.prove(assumptions, automation=False)
                except:
                    # orIf[Any,Left,Right] must not have been a usable theorem; use the default below.
                    break
    
    def sideEffects(self, knownTruth):
        '''
        Side-effect derivations to attempt automatically.
        '''
        from proveit.logic import Not
        if len(self.operands)==2:
            if self.operands[1] == Not(self.operands[0]):
                # (A or not(A)) is an unfolded Boolean
                return # stop to avoid infinite recursion.
        yield self.deriveInBool
        #yield self.deriveParts # added by JML 6/28/19

    def negationSideEffects(self, knownTruth):
        '''
        Side-effect derivations to attempt automatically for Not(A or B or .. or .. Z).
        '''
        yield self.deriveInBool # A or B or .. or .. Z in Booleans
        if len(self.operands) == 2: # Not(A or B)
            yield self.deduceNotLeftIfNeither # Not(A)
            yield self.deduceNotRightIfNeither # Not(B)

    def inBoolSideEffects(self, knownTruth):
        '''
        From (A or B or .. or Z) in Booleans deduce (A in Booleans), (B in Booleans), ...
        (Z in Booleans).
        '''
        yield self.deducePartsInBool
        
    def concludeNegation(self, assumptions):
        from ._theorems_ import falseOrFalseNegated, neitherIntro, notOrIfNotAny
        if self == falseOrFalseNegated.operand:
            return falseOrFalseNegated # the negation of (FALSE or FALSE)
        elif len(self.operands)==2:
            return neitherIntro.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
        else:
            from proveit.number import num
            return notOrIfNotAny.specialize({m: num(len(self.operands)), AA: self.operands}, assumptions=assumptions)
    
    def concludeViaBoth(self, assumptions):
        from ._theorems_ import orIfBoth
        assert len(self.operands) == 2        
        return orIfBoth.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
    
    def concludeViaOnlyLeft(self, assumptions):
        from ._theorems_ import orIfOnlyLeft
        assert len(self.operands) == 2        
        return orIfOnlyLeft.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
    
    def concludeViaOnlyRight(self, assumptions):
        from ._theorems_ import orIfOnlyRight
        assert len(self.operands) == 2        
        return orIfOnlyRight.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
                
    def deriveInBool(self, assumptions=USE_DEFAULTS):
        '''
        From (A or B or ... or Z) derive [(A or B or ... or Z) in Booleans].
        '''
        return inBool(self).prove(assumptions=assumptions)

    def deriveParts(self, assumptions=USE_DEFAULTS):
        r'''
        From (A or B or ... or Z)` derive each operand:
        A, B, ..., Z.
        '''
        for i in range(len(self.operands)):
            self.deriveInPart(i, assumptions)

    def deriveInPart(self, indexOrExpr, assumptions=USE_DEFAULTS):
        r'''
        From (A and ... and X and ... and Z)` derive X.  indexOrExpr specifies
        :math:`X` either by index or the expr.
        '''
        from ._theorems_ import anyFromAnd, leftFromAnd, rightFromAnd
        idx = indexOrExpr if isinstance(indexOrExpr, int) else list(self.operands).index(indexOrExpr)
        if idx < 0 or idx >= len(self.operands):
            raise IndexError("Operand out of range: " + str(idx))
        if len(self.operands)==2:
            pass
        else:
            from proveit.number import num
            mVal, nVal = num(idx), num(len(self.operands)-idx-1)
            return anyFromAnd.specialize({m:mVal, n:nVal, AA:self.operands[:idx], B:self.operands[idx], CC:self.operands[idx+1:]}, assumptions=assumptions)
    
    def deriveRightIfNotLeft(self, assumptions=USE_DEFAULTS):
        '''
        From (A or B) derive and return B assuming Not(A), inBool(B). 
        '''
        from ._theorems_ import rightIfNotLeft
        assert len(self.operands) == 2
        leftOperand, rightOperand = self.operands
        return rightIfNotLeft.specialize({A:leftOperand, B:rightOperand}, assumptions=assumptions)#.deriveConclusion(assumptions)

    def deriveLeftIfNotRight(self, assumptions=USE_DEFAULTS):
        '''
        From (A or B) derive and return A assuming inBool(A), Not(B).
        '''
        from ._theorems_ import leftIfNotRight
        assert len(self.operands) == 2
        leftOperand, rightOperand = self.operands
        return leftIfNotRight.specialize({A:leftOperand, B:rightOperand}, assumptions=assumptions)#.deriveConclusion(assumptions)

    def deriveViaSingularDilemma(self, conclusion, assumptions=USE_DEFAULTS):
        '''
        From (A or B) as self, and assuming A => C, B => C, and A and B are Booleans,
        derive and return the conclusion, C.  Self is (A or B).
        '''
        from ._theorems_ import singularConstructiveDilemma, singularConstructiveMultiDilemma
        if len(self.operands) == 2:
            return singularConstructiveDilemma.specialize({A:self.operands[0], B:self.operands[1], C:conclusion}, assumptions=assumptions)
        from proveit.number import num
        return singularConstructiveMultiDilemma.specialize({m: num(len(self.operands)), AA: self.operands, C:conclusion}, assumptions=assumptions)

    def deriveViaMultiDilemma(self, conclusion, assumptions=USE_DEFAULTS):
        '''
        From (A or B) as self, and assuming A => C, B => D, and A, B, C, and D are Booleans,
        derive and return the conclusion, C or D.
        '''
        from ._theorems_ import constructiveDilemma, destructiveDilemma, constructiveMultiDilemma, destructiveMultiDilemma
        from proveit.logic import Not, Or
        from proveit.number import num
        assert isinstance(conclusion, Or) and len(conclusion.operands) == len(self.operands), "deriveViaMultiDilemma requires conclusion to be a disjunction, the same number of operands as self."
        # Check for destructive versus constructive dilemma cases.
        if all(isinstance(operand, Not) for operand in self.operands) and all(isinstance(operand, Not) for operand in conclusion.operands):
            # destructive case.
            if len(self.operands) == 2:
                # From Not(C) or Not(D), A => C, B => D, conclude Not(A) or Not(B)
                return destructiveDilemma.specialize({C:self.operands[0].operand, D:self.operands[1].operand, A:conclusion.operands[0].operand, B:conclusion.operands[1].operand}, assumptions=assumptions)
            # raise NotImplementedError("Generalized destructive multi-dilemma not implemented yet.")
            # Iterated destructive case.  From (Not(A) or Not(B) or Not(C) or Not(D)) as self
            negatedOperandsSelf = [operand.operand for operand in self.operands]
            negatedOperandsConc = [operand.operand for operand in conclusion.operands]
            return destructiveMultiDilemma.specialize({m: num(len(self.operands)), AA: negatedOperandsSelf, BB: negatedOperandsConc}, assumptions=assumptions)
        else:
            # constructive case.
            if len(self.operands) == 2:
                # From (A or B), A => C, B => D, conclude C or D.
                return constructiveDilemma.specialize({A:self.operands[0], B:self.operands[1], C:conclusion.operands[0], D:conclusion.operands[1]}, assumptions=assumptions)
            #raise NotImplementedError("Generalized constructive multi-dilemma not implemented yet.")
            return constructiveMultiDilemma.specialize({m: num(len(self.operands)), AA: self.operands, BB: conclusion.operands},assumptions=assumptions)

    def deriveViaDilemma(self, conclusion, assumptions=USE_DEFAULTS):
        '''
        If the conclusion is also an Or operation with the same number of operands as
        self, try deriveViaMultiDilemma.  Otherwise, or if that fails, try
        deriveViaSingularDilemma.
        '''
        if isinstance(conclusion, Or) and len(conclusion.operands)==len(self.operands):
            try:
                return self.deriveViaMultiDilemma(conclusion, assumptions)
            except ProofFailure:
                pass
        return self.deriveViaSingularDilemma(conclusion, assumptions)

    def deduceLeftInBool(self, assumptions=USE_DEFAULTS):
        '''
        Deduce A in Booleans from (A or B) in Booleans.
        '''
        from ._axioms_ import leftInBool
        if len(self.operands) == 2:
            return leftInBool.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
        
    def deduceRightInBool(self, assumptions=USE_DEFAULTS):
        '''
        Deduce B in Booleans from (A or B) in Booleans.
        '''
        from ._axioms_ import rightInBool
        if len(self.operands) == 2:
            return rightInBool.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)

    def deducePartsInBool(self, assumptions=USE_DEFAULTS):
        '''
        Deduce A in Booleans, B in Booleans, ..., Z in Booleans
        from (A or B or ... or Z) in Booleans.
        '''
        for i in range(len(self.operands)):
            self.deducePartInBool(i, assumptions)        

    def deducePartInBool(self, indexOrExpr, assumptions=USE_DEFAULTS):
        '''
        Deduce X in Booleans from (A or B or .. or X or .. or Z) in Booleans
        provided X by expression or index number.
        '''
        from ._theorems_ import eachInBool
        from proveit.number import num
        idx = indexOrExpr if isinstance(indexOrExpr, int) else list(self.operands).index(indexOrExpr)
        if idx < 0 or idx >= len(self.operands):
            raise IndexError("Operand out of range: " + str(idx))
        if len(self.operands)==2:
            if idx==0: return self.deduceLeftInBool(assumptions)
            elif idx==1: return self.deduceRightInBool(assumptions)
        #attempt to replace with AA and CC over Amulti and Cmulti    
        return eachInBool.specialize({m:num(idx), n:num(len(self.operands)-idx-1), AA:self.operands[:idx], B:self.operands[idx], CC:self.operands[idx+1:]}, assumptions=assumptions)
                
    def deduceNotLeftIfNeither(self, assumptions=USE_DEFAULTS):
        '''
        Deduce not(A) assuming not(A or B) where self is (A or B). 
        '''
        from ._theorems_ import notLeftIfNeither
        assert len(self.operands) == 2
        leftOperand, rightOperand = self.operands
        return notLeftIfNeither.specialize({A:leftOperand, B:rightOperand}, assumptions=assumptions)

    def deduceNotRightIfNeither(self, assumptions=USE_DEFAULTS):
        '''
        Deduce not(B) assuming not(A or B) where self is (A or B). 
        '''
        from ._theorems_ import notRightIfNeither
        assert len(self.operands) == 2
        leftOperand, rightOperand = self.operands
        return notRightIfNeither.specialize({A:leftOperand, B:rightOperand}, assumptions=assumptions)

    def deduceDemorgansEquiv(self, assumptions=USE_DEFAULTS):
        '''
        # created by JML 6/28/19
        From A and B and C conclude Not(Not(A) or Not(B) or Not(C))
        '''
        from ._theorems_ import demorgansLawAndToOr, demorgansLawAndToOrBin
        from proveit.number import num
        if len(self.operands) == 2:
            return demorgansLawAndToOrBin.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
        else:
            return demorgansLawAndToOr.specialize({m:num(len(self.operands)), AA:self.operands}, assumptions=assumptions)

    def deriveCommonConclusion(self, conclusion, assumptions=USE_DEFAULTS):
        '''
        From (A or B) derive and return the provided conclusion C assuming A=>C, B=>C, A,B,C in BOOLEANS.
        '''
        from ._theorems_ import hypotheticalDisjunction
        from proveit.logic import Implies, compose
        # forall_{A in Bool, B in Bool, C in Bool} (A=>C and B=>C) => ((A or B) => C)
        assert len(self.operands) == 2
        leftOperand, rightOperand = self.operands
        leftImplConclusion = Implies(leftOperand, conclusion)
        rightImplConclusion = Implies(rightOperand, conclusion)
        # (A=>C and B=>C) assuming A=>C, B=>C
        compose([leftImplConclusion, rightImplConclusion], assumptions)
        return hypotheticalDisjunction.specialize({A:leftOperand, B:rightOperand, C:conclusion}, assumptions=assumptions).deriveConclusion(assumptions).deriveConclusion(assumptions)
        
    def evaluation(self, assumptions=USE_DEFAULTS):
        '''
        Given operands that evaluate to TRUE or FALSE, derive and
        return the equality of this expression with TRUE or FALSE. 
        '''
        from ._axioms_ import emptyDisjunction
        from ._axioms_ import orTT, orTF, orFT, orFF # load in truth-table evaluations
        if len(self.operands) == 0:
            return emptyDisjunction
        try:
            self.prove(assumptions)
        except ProofFailure:
            try:
                self.disprove(assumptions)
            except ProofFailure:
                raise EvaluationError("Unable to evaluate disjunction.")
        return Operation.evaluation(self, assumptions)

    def deriveContradiction(self, assumptions=USE_DEFAULTS):
        r'''
        From (A or B), and assuming not(A) and not(B), derive and return FALSE.
        '''
        from ._theorems_ import binaryOrContradiction, orContradiction
        if len(self.operands) == 2:
            return binaryOrContradiction.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
        else:
            from proveit.number import num
            return orContradiction.specialize({m:num(len(self.operands)), AA:self.operands}, assumptions=assumptions)

    def deriveGroup(self, beg, end, assumptions=USE_DEFAULTS):
        '''
        From (A or B or ... or Y or Z), assuming in Booleans and given beginning and end of group, derive and return
        (A or B ... or (l or ... or M) or ... or X or Z).
        '''
        from ._theorems_ import group
        from proveit.number import num
        if end <= beg:
            raise IndexError ("Beginning and end value must be of the form beginning < end.")
        if end > len(self.operands) -1:
            raise IndexError("End value must be less than length of expression.")
        return group.specialize({l :num(beg), m:num(end - beg), n: num(len(self.operands) - end), AA:self.operands[:beg], BB:self.operands[beg : end], CC: self.operands[end :]}, assumptions=assumptions)

    def deriveSwap(self, i, j, assumptions=USE_DEFAULTS):
        '''
        From (A or ... or H or I or J or ... or L or M or N or ... or Q), assuming in Booleans and given
        the beginning and end of the groups to be switched,
        derive and return (A or ... or H or M or J or ... or L or I or N or ... or Q).
        '''
        from ._theorems_ import swap
        from proveit.number import num
        if 0 < i < j < len(self.operands) - 1:
            return swap.specialize({l: num(i), m: num(j - i - 1), n: num(len(self.operands)-j - 1), AA: self.operands[:i], B: self.operands[i], CC: self.operands[i+1:j], D: self.operands[j], EE: self.operands[j + 1:]}, assumptions=assumptions)
        else:
            raise IndexError("Beginnings and ends must be of the type: 0<i<j<length.")

    def affirmViaContradiction(self, conclusion, assumptions=USE_DEFAULTS):
        '''
        From (A or B), derive the conclusion provided that the negated
        conclusion implies not(A) and not(B), and the conclusion is a Boolean.
        '''
        from proveit.logic.boolean.implication import affirmViaContradiction
        return affirmViaContradiction(self, conclusion, assumptions)

    def denyViaContradiction(self, conclusion, assumptions=USE_DEFAULTS):
        '''

        From (A or B), derive the negated conclusion provided that the
        conclusion implies both not(A) and not(B), and the conclusion is a Boolean.
        '''
        from proveit.logic.boolean.implication import denyViaContradiction
        return denyViaContradiction(self, conclusion, assumptions)
                                                
    def deduceInBool(self, assumptions=USE_DEFAULTS):
        '''
        Attempt to deduce, then return, that this 'or' expression is in the set of BOOLEANS.
        '''
        from ._theorems_ import binaryClosure, closure
        from proveit.number import num
        if len(self.operands) == 2:
            return binaryClosure.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
        else:
            return closure.specialize({m:num(len(self.operands)), AA:self.operands}, assumptions=assumptions)
        
    def concludeViaExample(self, trueOperand, assumptions=USE_DEFAULTS):
        '''
        From one true operand, conclude that this 'or' expression is true.
        Requires all of the operands to be in the set of BOOLEANS.
        '''
        from proveit.number import num
        from ._theorems_ import orIfAny, orIfLeft, orIfRight
        index = self.operands.index(trueOperand)
        if len(self.operands) == 2:
            if index == 0:
                return orIfLeft.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
            elif index == 1:
                return orIfRight.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)                
        return orIfAny.specialize({m:num(index), n:num(len(self.operands)-index-1), AA:self.operands[:index], B:self.operands[index], CC:self.operands[index+1:]}, assumptions=assumptions)

    def deduceUnaryEquiv(self, assumptions=USE_DEFAULTS):
        from proveit.logic.boolean.disjunction._theorems_ import unaryDisjunctionDef
        if len(self.operands) != 1:
            raise ValueError("Expression must have a single operand in order to invoke unaryDisjunctionDef")
        operand = self.operands[0]
        return unaryDisjunctionDef.specialize({A:operand}, assumptions = assumptions)