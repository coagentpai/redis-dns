import dns.rdtypes.IN.A 
import dns.rdtypes.ANY.MX 
import dns.rdtypes.ANY.CNAME
import dns.rdtypes.ANY.TXT
import dns.rdtypes.ANY.NS

class NS(dns.rdtypes.ANY.NS.NS):
    def __init__(self, target):
        super(NS, self).__init__(dns.rdataclass.ANY, dns.rdatatype.NS, target)
        pass
    pass # END Class NS

class MX(dns.rdtypes.ANY.MX.MX):
    def __init__(self, preference, exchange):
        super(MX, self).__init__(dns.rdataclass.IN, dns.rdatatype.MX, preference, exchange)
        pass
    pass # END Class MX

class A(dns.rdtypes.IN.A.A):
    def __init__(self, address):
        super(A, self).__init__(dns.rdataclass.IN, dns.rdatatype.A, address)
        pass
    pass # END Class A

class CNAME(dns.rdtypes.ANY.CNAME.CNAME):
    def __init__(self, target):
        super(CNAME, self).__init__(dns.rdataclass.ANY, dns.rdatatype.CNAME, target)
        pass
    pass # END Class CNAME


class TXT(dns.rdtypes.ANY.TXT.TXT):
    def __init__(self, text):
        super(TXT, self).__init__(dns.rdataclass.ANY, dns.rdatatype.TXT, text)
        pass
    pass # END Class TXT

__all__ = [MX, A, CNAME, TXT]
