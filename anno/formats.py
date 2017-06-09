


















class FormatCRUD(object):
    @classmethod
    def create_anno(cls, anno_id, **kwargs):
        '''knows nothing about the format of input:
           1. if `anno_id` arg is None, generate an id;
              any value in annotation for prop `id` is ignored.
           2. checks for `creator` prop, pull from auth if not present
           3. checks for `permissions` prop, sets default if not present
                default permission is public for read, creator for update,
                delete, and admin
        '''
        # need to generate anno_id for to-be-created anno?
        if anno_id is None:
            anno_id = uuid4()
        # validate webannotation json


        # conversion happens where????

        # call create_from_webanno

