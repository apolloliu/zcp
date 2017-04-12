#    Copyright  2017 EasyStack, Inc
#    Authors: Branty <jun.wang@easystack.cn>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import six


class Model(object):
    """Base class for storage API models."""

    def __init__(self, **kwds):
        self.fields = list(kwds)
        for k, v in six.iteritems(kwds):
            setattr(self, k, v)

    def as_dict(self):
        d = {}
        for f in self.fields:
            v = getattr(self, f)
            if isinstance(v, Model):
                v = v.as_dict()
            elif isinstance(v, list) and v and isinstance(v[0], Model):
                v = [sub.as_dict() for sub in v]
            d[f] = v
        return d


class Resource(Model):
    """Something for which sample data has been collected."""

    def __init__(self, resource_id, project_id,
                 first_sample_timestamp,
                 last_sample_timestamp,
                 source, user_id, metadata,
                 resource_name):
        """Create a new resource.

        :param resource_id: UUID of the resource
        :param project_id:  UUID of project owning the resource
        :param first_sample_timestamp: first sample timestamp captured
        :param last_sample_timestamp: last sample timestamp captured
        :param source:      the identifier for the user/project id definition
        :param user_id:     UUID of user owning the resource
        :param metadata:    most current metadata for the resource (a dict)
        :param resource_name:   resource display name
        """
        super(Resource, self).__init__(
            resource_id=resource_id,
            first_sample_timestamp=first_sample_timestamp,
            last_sample_timestamp=last_sample_timestamp,
            project_id=project_id,
            source=source,
            user_id=user_id,
            metadata=metadata,
            resource_name=resource_name)


class Statistics(Model):
    """Computed statistics based on a set of sample data."""
    def __init__(self, unit,
                 period, period_start, period_end,
                 duration, duration_start, duration_end,
                 groupby, **data):
        """Create a new statistics object.

        :param unit: The unit type of the data set
        :param period: The length of the time range covered by these stats
        :param period_start: The timestamp for the start of the period
        :param period_end: The timestamp for the end of the period
        :param duration: The total time for the matching samples
        :param duration_start: The earliest time for the matching samples
        :param duration_end: The latest time for the matching samples
        :param groupby: The fields used to group the samples.
        :param data: some or all of the following aggregates
           min: The smallest volume found
           max: The largest volume found
           avg: The average of all volumes found
           sum: The total of all volumes found
           count: The number of samples found
           aggregate: name-value pairs for selectable aggregates
        """
        super(Statistics, self).__init__(
            unit=unit,
            period=period,
            period_start=period_start,
            period_end=period_end,
            duration=duration,
            duration_start=duration_start,
            duration_end=duration_end,
            groupby=groupby,
            **data)
