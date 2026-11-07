from . import ashby, greenhouse, lever, recruitee, smartrecruiters, teamtailor, workable, workday

ADAPTERS = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "workday": workday.fetch,
    "teamtailor": teamtailor.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workable": workable.fetch,
    "ashby": ashby.fetch,
    "recruitee": recruitee.fetch,
}
