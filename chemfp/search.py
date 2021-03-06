"Ways to search an arena"

import _chemfp
import ctypes
import array


class SearchResult(object):
    def __init__(self, search_results, row):
        self._search_results = search_results
        self._row = row

    def __len__(self):
        return self._search_results._size(self._row)

    def __iter__(self):
        return iter(self._search_results._get_indices_and_scores(self._row))
        
    def clear(self):
        self._search_results._clear_row(self._row)

    def get_indices(self):
        return self._search_results._get_indices(self._row)

    def get_ids(self):
        ids = self._search_results.target_ids
        if ids is None:
            return None
        return [ids[i] for i in self._search_results._get_indices(self._row)]
    
    def get_scores(self):
        return self._search_results._get_scores(self._row)
        
    def get_ids_and_scores(self):
        ids = self._search_results.target_ids
        if ids is None:
            raise TypeError("target_ids are not available")
        return zip(self.get_ids(), self.get_scores())

    def get_indices_and_scores(self):
        return self._search_results._get_indices_and_scores(self._row)
            
    def reorder(self, ordering="decreasing-score"):
        self._search_results._reorder_row(self._row, ordering)
        
    @property
    def target_id(self):
        ids = self._search_results.target_ids
        if ids is None:
            return None
        return ids[self._row]

class SearchResults(_chemfp.SearchResults):
    def __init__(self, n, ids=None):
        super(SearchResults, self).__init__(n, ids)
        self._results = [SearchResult(self, i) for i in xrange(n)]
    def __iter__(self):
        return iter(self._results)

    def __getitem__(self, i):
        try:
            i = xrange(len(self))[i]
        except IndexError:
            raise IndexError("row index is out of range")
        return self._results[i]

    def iter_indices(self):
        for i in xrange(len(self)):
            yield self._get_indices(i)

    def iter_ids(self):
        ids = self.target_ids
        for indicies in self.iter_indices():
            yield [ids[idx] for idx in indicies]

    def iter_scores(self):
        for i in xrange(len(self)):
            yield self._get_scores(i)

    def iter_indices_and_scores(self):
        for i in xrange(len(self)):
            yield self[i]
    
    def iter_ids_and_scores(self):
        ids = self.target_ids
        for i in xrange(len(self)):
            yield [(ids[idx], score) for (idx, score) in self[i]]


        
def require_matching_fp_size(query_fp, target_arena):
    if len(query_fp) != target_arena.metadata.num_bytes:
        raise ValueError("query_fp uses %d bytes while target_arena uses %d bytes" % (
            len(query_fp), target_arena.metadata.num_bytes))

def require_matching_sizes(query_arena, target_arena):
    assert query_arena.metadata.num_bits is not None, "arenas must define num_bits"
    assert target_arena.metadata.num_bits is not None, "arenas must define num_bits"
    if query_arena.metadata.num_bits != target_arena.metadata.num_bits:
        raise ValueError("query_arena has %d bits while target_arena has %d bits" % (
            query_arena.metadata.num_bits, target_arena.metadata.num_bits))
    if query_arena.metadata.num_bytes != target_arena.metadata.num_bytes:
        raise ValueError("query_arena uses %d bytes while target_arena uses %d bytes" % (
            query_arena.metadata.num_bytes, target_arena.metadata.num_bytes))
    



def count_tanimoto_hits_fp(query_fp, target_arena, threshold):
    require_matching_fp_size(query_fp, target_arena)
    # Improve the alignment so the faster algorithms can be used
    query_start_padding, query_end_padding, query_fp = _chemfp.align_fingerprint(
        query_fp, target_arena.alignment, target_arena.storage_size)
                                                 
    counts = array.array("i", (0 for i in xrange(len(query_fp))))
    _chemfp.count_tanimoto_arena(threshold, target_arena.num_bits,
                                 query_start_padding, query_end_padding,
                                 target_arena.storage_size, query_fp, 0, 1,
                                 target_arena.start_padding, target_arena.end_padding,
                                 target_arena.storage_size, target_arena.arena,
                                 target_arena.start, target_arena.end,
                                 target_arena.popcount_indices,
                                 counts)
    return counts[0]


def count_tanimoto_hits(query_arena, target_arena, threshold):
    require_matching_sizes(query_arena, target_arena)

    counts = (ctypes.c_int*len(query_arena))()
    _chemfp.count_tanimoto_arena(threshold, target_arena.num_bits,
                                 query_arena.start_padding, query_arena.end_padding,
                                 query_arena.storage_size,
                                 query_arena.arena, query_arena.start, query_arena.end,
                                 target_arena.start_padding, target_arena.end_padding,
                                 target_arena.storage_size,
                                 target_arena.arena, target_arena.start, target_arena.end,
                                 target_arena.popcount_indices,
                                 counts)
    return counts    

def count_tanimoto_hits_symmetric(arena, threshold):
    N = len(arena)
    counts = (ctypes.c_int * N)()

    _chemfp.count_tanimoto_hits_arena_symmetric(
        threshold, arena.num_bits,
        arena.start_padding, arena.end_padding, arena.storage_size, arena.arena,
        0, N, 0, N,
        arena.popcount_indices,
        counts)

    return counts


def partial_count_tanimoto_hits_symmetric(counts, arena, threshold,
                                          query_start=0, query_end=None,
                                          target_start=0, target_end=None):
    N = len(arena)
    
    if query_end is None:
        query_end = N
    elif query_end > N:
        query_end = N
        
    if target_end is None:
        target_end = N
    elif target_end > N:
        target_end = N

    if query_end > len(counts):
        raise ValueError("counts array is too small for the given query range")
    if target_end > len(counts):
        raise ValueError("counts array is too small for the given target range")

    _chemfp.count_tanimoto_hits_arena_symmetric(
        threshold, arena.num_bits,
        arena.start_padding, arena.end_padding, arena.storage_size, arena.arena,
        query_start, query_end, target_start, target_end,
        arena.popcount_indices,
        counts)


# These all return indices into the arena!

def threshold_tanimoto_search_fp(query_fp, target_arena, threshold):
    require_matching_fp_size(query_fp, target_arena)

    # Improve the alignment so the faster algorithms can be used
    query_start_padding, query_end_padding, query_fp = _chemfp.align_fingerprint(
        query_fp, target_arena.alignment, target_arena.storage_size)


    results = SearchResults(1)
    _chemfp.threshold_tanimoto_arena(
        threshold, target_arena.num_bits,
        query_start_padding, query_end_padding, target_arena.storage_size, query_fp, 0, 1,
        target_arena.start_padding, target_arena.end_padding,
        target_arena.storage_size, target_arena.arena,
        target_arena.start, target_arena.end,
        target_arena.popcount_indices,
        results, 0)
    return results[0]


def threshold_tanimoto_search(query_arena, target_arena, threshold):
    require_matching_sizes(query_arena, target_arena)

    num_queries = len(query_arena)

    results = SearchResults(num_queries, target_arena.ids)
    if num_queries:
        _chemfp.threshold_tanimoto_arena(
            threshold, target_arena.num_bits,
            query_arena.start_padding, query_arena.end_padding,
            query_arena.storage_size, query_arena.arena, query_arena.start, query_arena.end,
            target_arena.start_padding, target_arena.end_padding,
            target_arena.storage_size, target_arena.arena, target_arena.start, target_arena.end,
            target_arena.popcount_indices,
            results, 0)
    
    return results

def threshold_tanimoto_search_symmetric(arena, threshold, include_lower_triangle=True):
    assert arena.popcount_indices
    N = len(arena)
    results = SearchResults(N, arena.ids)

    if N:
        _chemfp.threshold_tanimoto_arena_symmetric(
            threshold, arena.num_bits,
            arena.start_padding, arena.end_padding, arena.storage_size, arena.arena,
            0, N, 0, N,
            arena.popcount_indices,
            results)

        if include_lower_triangle:
            _chemfp.fill_lower_triangle(results, N)
        
    return results



#def XXXpartial_threshold_tanimoto_search(results, query_arena, target_arena, threshold,
#                                      results_offsets=0):
#    pass

def partial_threshold_tanimoto_search_symmetric(results, arena, threshold,
                                                query_start=0, query_end=None,
                                                target_start=0, target_end=None):
    assert arena.popcount_indices
    N = len(arena)
    
    if query_end is None:
        query_end = N
    elif query_end > N:
        query_end = N
        
    if target_end is None:
        target_end = N
    elif target_end > N:
        target_end = N

    if query_end > N:
        raise ValueError("counts array is too small for the given query range")
    if target_end > N:
        raise ValueError("counts array is too small for the given target range")

    if N:
        _chemfp.threshold_tanimoto_arena_symmetric(
            threshold, arena.num_bits,
            arena.start_padding, arena.end_padding, arena.storage_size, arena.arena,
            query_start, query_end, target_start, target_end,
            arena.popcount_indices,
            results)


def fill_lower_triangle(results):
    _chemfp.fill_lower_triangle(results, len(results))




# These all return indices into the arena!

def knearest_tanimoto_search_fp(query_fp, target_arena, k, threshold):
    require_matching_fp_size(query_fp, target_arena)
    query_start_padding, query_end_padding, query_fp = _chemfp.align_fingerprint(
        query_fp, target_arena.alignment, target_arena.storage_size)
    
    if k < 0:
        raise ValueError("k must be non-negative")

    results = SearchResults(1)
    _chemfp.knearest_tanimoto_arena(
        k, threshold, target_arena.num_bits,
        query_start_padding, query_end_padding, target_arena.storage_size, query_fp, 0, 1,
        target_arena.start_padding, target_arena.end_padding,
        target_arena.storage_size, target_arena.arena, target_arena.start, target_arena.end,
        target_arena.popcount_indices,
        results, 0)
    _chemfp.knearest_results_finalize(results, 0, 1)

    return results[0]

def knearest_tanimoto_search(query_arena, target_arena, k, threshold):
    require_matching_sizes(query_arena, target_arena)

    num_queries = len(query_arena)

    results = SearchResults(num_queries, target_arena.ids)

    _chemfp.knearest_tanimoto_arena(
        k, threshold, target_arena.num_bits,
        query_arena.start_padding, query_arena.end_padding,
        query_arena.storage_size, query_arena.arena, query_arena.start, query_arena.end,
        target_arena.start_padding, target_arena.end_padding,
        target_arena.storage_size, target_arena.arena, target_arena.start, target_arena.end,
        target_arena.popcount_indices,
        results, 0)
    
    _chemfp.knearest_results_finalize(results, 0, num_queries)
    
    return results


def knearest_tanimoto_search_symmetric(arena, k, threshold):
    N = len(arena)

    results = SearchResults(N, arena.ids)

    _chemfp.knearest_tanimoto_arena_symmetric(
        k, threshold, arena.num_bits,
        arena.start_padding, arena.end_padding, arena.storage_size, arena.arena,
        0, N, 0, N,
        arena.popcount_indices,
        results)
    _chemfp.knearest_results_finalize(results, 0, N)
    
    return results



#def partial_knearest_tanimoto_search(results, arena, k, threshold, results_offset=0):
#    pass
#
#def partial_knearest_tanimoto_search_symmetric(results, arena, k, threshold,
#                                               query_start=0, query_end=None,
#                                               target_start=0, target_end=None):
#    pass
