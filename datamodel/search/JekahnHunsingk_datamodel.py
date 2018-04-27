'''
Created on Oct 20, 2016
@author: Rohan Achar
'''
from rtypes.pcc.attributes import dimension, primarykey, predicate
from rtypes.pcc.types.subset import subset
from rtypes.pcc.types.set import pcc_set
from rtypes.pcc.types.projection import projection
from rtypes.pcc.types.impure import impure
from datamodel.search.server_datamodel import Link, ServerCopy

@pcc_set
class JekahnHunsingkLink(Link):
    USERAGENTSTRING = "JekahnHunsingk"

    @dimension(str)
    def user_agent_string(self):
        return self.USERAGENTSTRING

    @user_agent_string.setter
    def user_agent_string(self, v):
        # TODO (rachar): Make it such that some dimensions do not need setters.
        pass


@subset(JekahnHunsingkLink)
class JekahnHunsingkUnprocessedLink(object):
    @predicate(JekahnHunsingkLink.download_complete, JekahnHunsingkLink.error_reason)
    def __predicate__(download_complete, error_reason):
        return not (download_complete or error_reason)


@impure
@subset(JekahnHunsingkUnprocessedLink)
class OneJekahnHunsingkUnProcessedLink(JekahnHunsingkLink):
    __limit__ = 1

    @predicate(JekahnHunsingkLink.download_complete, JekahnHunsingkLink.error_reason)
    def __predicate__(download_complete, error_reason):
        return not (download_complete or error_reason)

@projection(JekahnHunsingkLink, JekahnHunsingkLink.url, JekahnHunsingkLink.download_complete)
class JekahnHunsingkProjectionLink(object):
    pass
