import re

from dark.simplify import simplifyTitle


class TitleFilter(object):
    """
    Provide an acceptance test for sequence titles.

    @param whitelist: If not C{None}, a set of exact titles that are always
        acceptable.
    @param blacklist: If not C{None}, a set of exact titles that are never
        acceptable.
    @param positiveRegex: If not C{None}, a regex that sequence titles must
        match.
    @param negativeRegex: If not C{None}, a regex that sequence titles must
        not match.
    @param truncateAfter: A C{str} that titles will be truncated beyond. If
        a truncated title has already been seen, that title will no longer
        be acceptable.
    """

    REJECT = 0
    WHITELIST_ACCEPT = 1
    DEFAULT_ACCEPT = 2

    def __init__(self, whitelist=None, blacklist=None, positiveRegex=None,
                 negativeRegex=None, truncateAfter=None):
        self._whitelist = whitelist
        self._blacklist = blacklist
        if truncateAfter is None:
            self._truncated = None
        else:
            self._truncateAfter = truncateAfter
            self._truncated = {}

        if positiveRegex is None:
            self._positiveRegex = None
        else:
            self._positiveRegex = re.compile(positiveRegex, re.I)

        if negativeRegex is None:
            self._negativeRegex = None
        else:
            self._negativeRegex = re.compile(negativeRegex, re.I)

    def accept(self, title):
        """
        Return a value (see below) to indicate if a title is acceptable (and,
        if so, in what way).

        @param title: A C{str} sequence title.
        @return: An C{int} to indicate an acceptable title or not. This will be

            C{self.REJECT} if the title is unacceptable.
            C{self.WHITELIST_ACCEPT} if the title is whitelisted.
            C{self.DEFAULT_ACCEPT} if the title is acceptable by default.

            These three values are needed so our caller can distinguish between
            the two reasons for acceptance.
        """
        if self._whitelist and title in self._whitelist:
            return self.WHITELIST_ACCEPT

        if self._blacklist and title in self._blacklist:
            return self.REJECT

        if self._truncated is not None:
            # Titles start with something like gi|525472786|emb|HG313807.1|
            # that we need to skip.
            titleSansId = title.split(' ', 1)[1]
            truncated = simplifyTitle(titleSansId, self._truncateAfter)
            if truncated in self._truncated:
                # We've already seen this (truncated) title. Reject unless
                # this is the original title that we truncated to make this
                # entry. That title must continue to be accepted.
                if self._truncated[truncated] == title:
                    return self.DEFAULT_ACCEPT
                else:
                    return self.REJECT
            else:
                self._truncated[truncated] = title

        # Do the title regex tests last, since they are slowest.
        if self._positiveRegex and self._positiveRegex.search(title) is None:
            return self.REJECT

        if (self._negativeRegex and
                self._negativeRegex.search(title) is not None):
            return self.REJECT

        return self.DEFAULT_ACCEPT


class HitInfoFilter(object):
    """
    Provide an acceptance test for sequence hit info.

    @param minSequenceLen: sequences of lesser length are unacceptable.
    @param maxSequenceLen: sequences of greater length are unacceptable.
    @param minMatchingReads: sequences that are matched by fewer reads
        are unacceptable.
    @param maxMeanEValue: sequences that are matched with a mean e-value
        that is greater are unacceptable.
    @param maxMedianEValue: sequences that are matched with a median
        e-value that is greater are unacceptable.
    @param withEBetterThan: if the best (minimum) e-value for a hit is not
        as good as (i.e., is higher than) this value, elide the hit. E.g.,
        suppose we are passed a value of 1e-20, then we should reject any
        hit whose best (i.e., lowest) e-value is worse (bigger) than 1e-20.
        So a hit with minimal e-value of 1e-10 would not be reported,
        whereas a hit with a minimal e-value of 1e-30 would be.
    """

    def __init__(self, minSequenceLen=None, maxSequenceLen=None,
                 minMatchingReads=None, maxMeanEValue=None,
                 maxMedianEValue=None, withEBetterThan=None):
            self._minSequenceLen = minSequenceLen
            self._maxSequenceLen = maxSequenceLen
            self._minMatchingReads = minMatchingReads
            self._maxMeanEValue = maxMeanEValue
            self._maxMedianEValue = maxMedianEValue
            self._withEBetterThan = withEBetterThan

    def accept(self, hitInfo):
        """
        Return C{True} if the passed hit info is acceptable.

        @param hitInfo: A C{dict} with keys:
            readCount:
            eValues:
            length:
            readNums:
            eMean:
            eMedian:
            eMin:

        @return: A C{bool} to indicate acceptable hit info or not.
        """
        return not (
            (self._minSequenceLen is not None and
             hitInfo['length'] < self._minSequenceLen) or
            (self._maxSequenceLen is not None and
             hitInfo['length'] > self._maxSequenceLen) or
            (self._minMatchingReads is not None and
             hitInfo['readCount'] < self._minMatchingReads) or
            (self._maxMeanEValue is not None and
             hitInfo['eMean'] > self._maxMeanEValue) or
            (self._maxMedianEValue is not None and
             hitInfo['eMedian'] > self._maxMedianEValue) or
            (self._withEBetterThan is not None and
             hitInfo['eMin'] > self._withEBetterThan))


class BitScoreFilter(object):
    """
    Provide an acceptance test for sequence hit bit scores.

    @param minMeanBitScore: sequences that are matched with a mean bit score
        that is greater are unacceptable.
    @param minMedianBitScore: sequences that are matched with a median
        bit score that is greater are unacceptable.
    @param withBitScoreBetterThan: if the best bit score for a hit is not
        as good as this value, elide the hit.
    """

    def __init__(self, minMeanBitScore=None, minMedianBitScore=None,
                 withBitScoreBetterThan=None):
            self._minMeanBitScore = minMeanBitScore
            self._minMedianBitScore = minMedianBitScore
            self._withBitScoreBetterThan = withBitScoreBetterThan

    def accept(self, hitInfo):
        """
        Return C{True} if the bit scores in the passed hit info is acceptable.

        @param hitInfo: A C{dict} with at least the following keys:
            bitScores:
            bitScoreMean:
            bitScoreMedian:
            bitScoreMax:

        @return: A C{bool} to indicate acceptable hit info or not.
        """
        return not (
            (self._minMeanBitScore is not None and
             hitInfo['bitScoreMean'] < self._minMeanBitScore) or
            (self._minMedianBitScore is not None and
             hitInfo['bitScoreMedian'] < self._minMedianBitScore) or
            (self._withBitScoreBetterThan is not None and
             hitInfo['bitScoreMax'] < self._withBitScoreBetterThan))
