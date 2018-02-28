from proveit._core_.expression import Expression
from proveit._core_.expression.lambda_expr.lambda_expr import Lambda
from proveit._core_.expression.label import Literal, Variable
from proveit._core_.defaults import USE_DEFAULTS

class Indexed(Expression):
    '''
    An Indexed Expression expresses a Variable,
    representing an ExprList or ExprTensor, being indexed
    to yield an element.
    
    Upon substitution, it automatically performs the indexing
    if the indexed expression is a composite and the
    difference between the index and base is a known
    integer (or list of integers).
    '''
    
    def __init__(self, var, index_or_indices, base=1):
        from composite import Composite, singleOrCompositeExpression, compositeExpression
        if not isinstance(var, Variable):
            raise TypeError("'var' being indexed should be a Variable")
        index_or_indices = singleOrCompositeExpression(index_or_indices)
        if isinstance(index_or_indices, Composite):
            # a composite of multiple indices
            self.indices = index_or_indices 
        else:
            # a single index
            self.index = index_or_indices
            # wrap a single index in a composite for convenience
            self.indices = compositeExpression(self.index)
        if not isinstance(base, int):
            raise TypeError("'base' should be an integer")
        Expression.__init__(self, ['Indexed', self.base], [var, index_or_indices])
        self.var = var
        self.base = base
    
    """
    def string(self, **kwargs):
        # fence by default (unless it is within an Embed
        fence =  kwargs['fence'] if 'fence' in kwargs else True 
        innerStr = self.first().string() + ', ..., ' + self.last().string()
        return maybeFenced('string', innerStr, fence=fence)

    def latex(self, **kwargs):
        # fence by default (unless it is within an Embed
        fence =  kwargs['fence'] if 'fence' in kwargs else True
        innerStr = self.first().latex() + ', \ldots, ' + self.last().latex()
        return maybeFenced('latex', innerStr, fence=fence)
    """
    
    def substituted(self, exprMap, relabelMap = None, reservedVars = None, assumptions=USE_DEFAULTS, requirements=None):
        '''
        Returns this expression with the substitutions made 
        according to exprMap and/or relabeled according to relabelMap.
        If the indexed variable has been replaced with a Composite
        (ExprList or ExprTensor), this should return the
        indexed element.  Only a Variable should be indexed via
        a Indexed expression; once the Variable is replaced with
        a Composite, the indexing should be actualized.
        '''
        from composite import Composite, _simplifiedCoord
        from expr_list import ExprList
        from expr_tensor import ExprTensor
        
        subbed_var = self.var.substituted(exprMap, relabelMap, reservedVars)
        subbed_indices = self.indices.substituted(exprMap, relabelMap, reservedVars)
        
        if isinstance(subbed_var, Composite):
            # The indexed expression is a composite.
            # Now see if the indices can be simplified to integers; if so,
            # we can attempt to extract the specific element.
            # If there is an IndexingError (i.e., we cannot get the element
            # because the Composite has an unexpanding Iter), 
            # default to returning the subbed Indexed.
            indexing_requirements = []
            indices = [_simplifiedCoord(index, assumptions, indexing_requirements) for index in subbed_indices]
            requirements += indexing_requirements
            if isinstance(subbed_var, ExprList):
                return subbed_var.getElem(indices[0], assumptions=assumptions, requirements=requirements)
            elif isinstance(subbed_var, ExprTensor):
                return subbed_var.getElem(indices, assumptions=assumptions, requirements=requirements)
        
        # If the subbed_var has not been replaced with a Composite,
        # just return the Indexed operation with the substitutions made.
        return Indexed(subbed_var, subbed_indices, base=self.base)

    def iterRanges(self, iterParams, startArgs, endArgs, exprMap, relabelMap = None, reservedVars = None, assumptions=USE_DEFAULTS, requirements=None):
        '''
        Considering a substitution defined via exprMap, relabelMap, etc, and
        index iteration defined by substituting the "iteration parameters" over
        the range from the "starting arguments" to the "ending arguments", yield
        disjoint sub-ranges that covers occupied portions of the full range
        in a manner that keeps different inner iterations separate.  In particular,
        when the Indexed variable is substituted with a Composite, the
        iteration range is broken up for the different Iter entries that
        are contained in this Composite.  If it is not substituted with
        a composite, the full range is simply yielded.
        '''
        from composite import Composite, IndexingError
        from expr_list import ExprList
        from proveit.logic import Equals
        from proveit.lambda_map import invert
        
        subbed_var = self.var.substituted(exprMap, relabelMap, reservedVars, assumptions, requirements)
        subbed_indices = self.indices.substituted(exprMap, relabelMap, reservedVars, assumptions, requirements)
        if isinstance(subbed_var, Composite):
            # We cannot substitute in a Composite without doing an iteration over it.
            # Only certain iterations are allowed in this manner however.
            
            start_indices = []
            end_indices = []
            for subbed_index, iterParam, startArg, endArg in zip(subbed_indices, iterParams, startArgs, endArgs):
                if iterParam not in subbed_index:
                    raise IndexingError("Iteration parameter not contained in the substituted index")
                start_indices.append(subbed_index.substituted({iterParam:startArg}))
                end_indices.append(subbed_index.substituted({iterParam:endArg}))
            
            if isinstance(subbed_var, ExprList):
                assert len(start_indices) == len(end_indices) == 1, "Lists are 1-dimensional and should be singly-indexed"
                entryRangeGenerator = subbed_var.entryRanges(start_indices[0], end_indices[0])
            else:
                entryRangeGenerator = subbed_var.entryRanges(start_indices, end_indices)
            
            for (intersection_start, intersection_end) in entryRangeGenerator:
                # We must put it terms of iter parameter values (arguments) via inverting the index_expr.
                def coord2param(axis, coord):
                    if subbed_indices[axis] == iterParams[axis]:
                        return coord # direct indexing that does not need to be inverted
                    # The indexing is not direct; for example, x_{f(p)}.
                    # We need to invert f to obtain p from f(p)=coord and register the inversion as a requirement:
                    # f(p) = coord.
                    param = invert(Lambda(iterParams[axis], subbed_indices[axis]), coord, assumptions=assumptions)
                    inversion = Equals(subbed_indices[axis].substituted({iterParams[axis]:param}), coord)
                    requirements.append(inversion.prove(assumptions=assumptions))
                    return param
                param_start = tuple([coord2param(axis, i) for axis, i in enumerate(intersection_start)])
                param_end = tuple([coord2param(axis, i) for axis, i in enumerate(intersection_end)])
                yield (param_start, param_end)
                        
        else:
            yield (startArgs, endArgs)
            
    """  
    def iterated(self, iterParams, startIndices, endIndices, exprMap, relabelMap = None, reservedVars = None, assumptions=USE_DEFAULTS, requirements=None):
        from proveit.number import proven_sort, zero, one, num, Add, Subtract, Greater
        
        subbed_var = self.indexed_expr.substituted(exprMap, relabelMap, reservedVars, assumptions, requirements)
        if isinstance(subbed_var, Composite):
            # We cannot substitute in a Composite without doing an iteration over it.
            # Only certain iterations are allowed in this manner however.
            
            if isinstance(subbed_var, ExprTenosr):
                tensor = subbed_var
                if len(iterParams) != len(self.indices):
                    raise IndexingError("Mismatch of ...")
                    
                for axis in xrange(tensor.ndims): # for each axis
                    if iterParams[axis] not in self.indices[axis]:
                        raise IndexingError("Mismatch of ...")
                    index_expr = self.indices[axis]
                    start_index = index_expr.substituted({iterParams[axis]:startIndices[axis]})
                    end_index = index_expr.substituted({iterParams[axis]:endIndices[axis]})
                    
                    sorted_coord_list = tensor.sortedCoordLists[axis]
                    coord_sorting_relation = proven_sort(sorted_coord_list + [start_index, end_index])
                    sorted_coords = list(coord_sorting_relation.operands)
                    
                
            
        else:
            yield self.substituted(exprMap, relabelMap, reservedVars, assumptions, requirements)

        
        
        if self.var in iterParams:
            raise IndexedError("It makes no sense to iterate over an Indexed's Variable.")
        if len(set(iterParams).intersection(self.indices.freeVars())) > 0:
            pass
        
        subbed_indexed_expr = 
        if isinstance(subbed_inde
    """

class IndexedError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
