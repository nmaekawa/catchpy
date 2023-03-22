import logging
from datetime import datetime

import dateutil
import dateutil.parser
from django.db import DatabaseError, DataError, IntegrityError, transaction
from django.db.models import Q

from .anno_defaults import (
    ANNO,
    CATCH_DEFAULT_PLATFORM_NAME,
    MEDIA_TYPES,
    PURPOSE_COMMENTING,
    PURPOSE_REPLYING,
    PURPOSE_TAGGING,
    PURPOSES,
    RESOURCE_TYPES,
)
from .errors import (
    AnnoError,
    DuplicateAnnotationIdError,
    InvalidAnnotationPurposeError,
    InvalidAnnotationTargetTypeError,
    InvalidInputWebAnnotationError,
    InvalidTargetMediaTypeError,
    MissingAnnotationError,
    TargetAnnotationForReplyMissingError,
)
from .json_models import Catcha
from .models import Anno, Tag, Target
from .search import query_userid, query_username
from .utils import generate_uid

logger = logging.getLogger(__name__)


#
# note on nomenclature
# catcha: a json webannotation, validated
# anno: an instance of Anno model
#


class CRUD(object):
    @classmethod
    def get_anno(cls, anno_id):
        """filters out the soft deleted instances."""
        try:
            anno = Anno._default_manager.get(pk=anno_id)
        except Anno.DoesNotExist:
            return None
        if anno.anno_deleted:
            return None
        return anno

    @classmethod
    def _group_body_items(cls, catcha):
        """sort out body items into text, format, tags, reply_to.

        modifies input `catcha['body']['items']` (removes duplicate tags)
        reply_to is the actual Anno model
        """
        body = catcha["body"]
        reply = False
        body_text = ""
        body_format = ""
        tags = []
        body_json = []
        for b in body["items"]:
            if b["purpose"] == PURPOSE_COMMENTING:
                body_text = b["value"]
                body_format = b["format"] if "format" in b else "text/plain"
                body_json.append(b)
            elif b["purpose"] == PURPOSE_REPLYING:
                reply = True
                body_text = b["value"]
                body_format = b["format"] if "format" in b else "text/plain"
                body_json.append(b)
            elif b["purpose"] == PURPOSE_TAGGING:
                if b["value"] not in tags:  # don't duplicate
                    tags.append(b["value"])
                    body_json.append(b)
            else:
                raise InvalidAnnotationPurposeError(
                    (
                        "body_item[purpose] should be in ({}), found({})" "in anno({})"
                    ).format(",".join(PURPOSES), b["purpose"], catcha["id"])
                )

        # replace with tag list clear of duplicates
        catcha["body"]["items"] = body_json

        reply_to = None
        reply_to_anno = None
        if reply:
            reply_to = cls.find_targets_of_mediatype(catcha, ANNO)
            if not reply_to:
                raise TargetAnnotationForReplyMissingError(
                    "missing parent reference for reply anno({})".format(catcha["id"])
                )
            # BEWARE: not checking, grabbing the first target
            reply_to = reply_to[0]["source"]
            reply_to_anno = cls.get_anno(reply_to)
            if reply_to_anno is None:
                raise TargetAnnotationForReplyMissingError(
                    "missing parent({}) for reply anno({})".format(
                        reply_to, catcha["id"]
                    )
                )

        return {
            "text": body_text,
            "format": body_format,
            "reply_to": reply_to_anno,
            "tags": tags,
        }

    @classmethod
    def _create_taglist(cls, taglist):
        """creates tags if do not exist already."""
        tags = []  # list of Tag instances
        for t in taglist:
            try:
                tag = Tag._default_manager.get(tag_name=t)
            except Tag.DoesNotExist:
                tag = Tag(tag_name=t)
                tag.save()
            tags.append(tag)
        return tags

    @classmethod
    def _create_targets_for_annotation(cls, anno, catcha):
        """creates Target instances, expects anno saved already."""
        t_list = []
        target = catcha["target"]
        if target["type"] not in RESOURCE_TYPES:
            raise InvalidAnnotationTargetTypeError(
                "target type should be in({}), found({}) in anno({})".format(
                    ",".join(RESOURCE_TYPES), target["type"], anno.anno_id
                )
            )
        anno.target_type = target["type"]
        for t in target["items"]:
            if t["type"] not in MEDIA_TYPES:
                raise InvalidTargetMediaTypeError(
                    (
                        "target media should be in ({}), found ({}) in " "anno({})"
                    ).format(MEDIA_TYPES, t["type"], anno.anno_id)
                )

            t_item = Target(
                target_source=t["source"], target_media=t["type"], anno=anno
            )
            t_list.append(t_item)

        return t_list

    @classmethod
    def _create_from_webannotation(cls, catcha, preserve_create=False):
        """creates new annotation instance and saves in db."""

        # fetch reply-to if it's a reply
        body = cls._group_body_items(catcha)

        # fill up derived properties in catcha
        catcha["totalReplies"] = 0

        try:
            with transaction.atomic():
                a = Anno(
                    anno_id=catcha["id"],
                    schema_version=catcha["schema_version"],
                    creator_id=catcha["creator"]["id"],
                    creator_name=catcha["creator"]["name"],
                    anno_reply_to=body["reply_to"],
                    can_read=catcha["permissions"]["can_read"],
                    can_update=catcha["permissions"]["can_update"],
                    can_delete=catcha["permissions"]["can_delete"],
                    can_admin=catcha["permissions"]["can_admin"],
                    body_text=body["text"],
                    body_format=body["format"],
                    raw=catcha,
                )

                # validate  target objects
                target_list = cls._create_targets_for_annotation(a, catcha)

                # create anno, target, and tags relationship as transaction
                a.save()  # need to save before setting relationships
                for t in target_list:
                    t.save()
                tags = cls._create_taglist(body["tags"])
                a.anno_tags.set(tags)

                # warn: order is important, update "created" after the first
                # save, or it won't take effect - first save is auto-now_add
                if preserve_create:
                    a.created = cls._get_original_created(catcha)

                a.raw["created"] = a.created.replace(microsecond=0).isoformat()
                a.save()
        except IntegrityError as e:
            msg = "integrity error creating anno({}): {}".format(catcha["id"], e)
            logger.error(msg, exc_info=True)
            raise DuplicateAnnotationIdError(msg)
        except DataError:
            msg = "tag too long for anno({})".format(catcha["id"])
            logger.error(msg, exc_info=True)
            raise InvalidInputWebAnnotationError(msg)
        else:
            return a

    @classmethod
    def _get_original_created(cls, catcha):
        """convert `created` from catcha or return current date."""
        try:
            original_date = dateutil.parser.parse(catcha["created"])
        except (TypeError, OverflowError, KeyError) as e:
            msg = (
                "error converting iso8601 `created` date in anno({}) "
                "copy, setting a fresh date: {}"
            ).format(catcha["id"], str(e))
            logger.error(msg, exc_info=True)
            original_date = datetime.now(dateutil.tz.tzutc()).replace(microsecond=0)
        else:
            return original_date

    @classmethod
    def _update_from_webannotation(cls, anno, catcha):
        """updates anno according to catcha input.

        recreates list of tags and targets every time
        """
        # fetch reply-to if it's a reply
        body = cls._group_body_items(catcha)

        # fill up derived properties in catcha
        catcha["totalReplies"] = anno.total_replies
        catcha["id"] = anno.anno_id

        # update the annotation object
        anno.schema_version = catcha["schema_version"]
        anno.creator_id = catcha["creator"]["id"]
        anno.creator_name = catcha["creator"]["name"]
        anno.anno_reply_to = body["reply_to"]
        anno.can_read = catcha["permissions"]["can_read"]
        anno.can_update = catcha["permissions"]["can_update"]
        anno.can_delete = catcha["permissions"]["can_delete"]
        anno.can_admin = catcha["permissions"]["can_admin"]
        anno.body_text = body["text"]
        anno.body_format = body["format"]
        anno.raw = catcha

        try:
            with transaction.atomic():
                # validate  input target objects
                target_list = cls._create_targets_for_annotation(anno, catcha)
                # remove all targets from annotation object
                cls._delete_targets(anno)
                # persist input target objects
                for t in target_list:
                    t.save()
                # dissociate tags from annotation
                anno.anno_tags.clear()
                # create tags
                if body["tags"]:
                    tags = cls._create_taglist(body["tags"])
                    anno.anno_tags.set(tags)
                anno.save()
        except (IntegrityError, DataError, DatabaseError) as e:
            msg = "-failed to create anno({}): {}".format(anno.anno_id, str(e))
            logger.error(msg, exc_info=True)
            raise InvalidInputWebAnnotationError(msg)
        else:
            return anno

    @classmethod
    def _delete_targets(cls, anno):
        targets = anno.target_set.all()
        for t in targets:
            t.delete()
        return targets

    @classmethod
    def delete_anno(cls, anno):
        if anno.anno_deleted:
            logger.warn("anno({}) already soft deleted".format(anno.anno_id))
            raise MissingAnnotationError("anno({}) not found".format(anno.anno_id))

        with transaction.atomic():
            # delete replies as well
            for a in anno.replies:
                try:
                    cls.delete_anno(a)
                except MissingAnnotationError:
                    pass  # ignore if already deleted

            anno.mark_as_deleted()
            anno.save()
        return anno

    @classmethod
    def read_anno(cls, anno):
        if anno.anno_deleted:
            logger.warning("anno({}) soft deleted".format(anno.anno_id))
            raise MissingAnnotationError("anno({}) not found".format(anno.anno_id))

        return anno

    @classmethod
    def find_targets_of_mediatype(cls, catcha, mediatype):
        parent = []
        for t in catcha["target"]["items"]:
            if t["type"] == mediatype:
                parent.append(t)
        return parent

    @classmethod
    def is_identical_permissions(cls, catcha1, catcha2):
        """check if there's any difference between permission."""
        for p in ["can_read", "can_update", "can_delete", "can_admin"]:
            if set(catcha1["permissions"][p]) != set(catcha2["permissions"][p]):
                return False
        return True

    @classmethod
    def update_anno(cls, anno, catcha):
        """updates anno according to catcha input.

        recreates list of tags and targets every time
        """
        if anno.anno_deleted:
            logger.error(
                "try to update deleted anno({})".format(anno.anno_id), exc_info=True
            )
            raise MissingAnnotationError("anno({}) not found".format(anno.anno_id))
        try:
            cls._update_from_webannotation(anno, catcha)
        except AnnoError as e:
            msg = "failed to save anno({}) during update operation: {}".format(
                anno.anno_id, str(e)
            )
            logger.error(msg, exc_info=True)
            raise e
        return anno

    @classmethod
    def create_anno(cls, catcha, preserve_create=False):
        """creates new instance of Anno model.

        expects `id` in catcha['id']

        when preserve_date=True, keeps the original `created` date
        errors in date parsing _silently_ render fresh `created` date.
        """
        if "id" not in catcha:
            # counting that caller fills up with proper id
            msg = "cannot not generate an id for annotation to-be-created"
            logger.error(msg, exc_info=True)
            raise AnnoError(msg)

        try:
            anno = cls._create_from_webannotation(catcha, preserve_create)
        except AnnoError as e:
            msg = "*failed to create anno({}) - {}".format(catcha["id"], str(e))
            logger.error(msg, exc_info=True)
            raise e

        return anno

    #####
    #
    # for the lack of better name and place
    # here goes the non-crud operations on models
    #

    @classmethod
    def import_annos(cls, catcha_list):
        """import a list of json catcha objects.

        CAUTION: this operation is done in steps and is not atomic.
        intermediate state between steps are not consistent and
        IS NOT MEANT to be an api endpoint.
        """
        discarded = []
        imported = []
        deleted = []
        reply = []

        # order by creation date (try to prevent import reply before parent)
        ordered_catcha_list = sorted(catcha_list, key=lambda k: k["created"])

        for c in ordered_catcha_list:
            logger.debug("processing anno_id({})".format(c["id"]))
            if Catcha.is_reply(c):  # leave replies for later
                logger.debug("({}) is reply".format(c["id"]))
                reply.append(c)
                continue  # leave reply for later

            if "deleted" in c["platform"] and c["platform"]["deleted"]:
                logger.debug("({}) is deleted".format(c["id"]))
                del c["platform"]["deleted"]  # remove before saving json
                deleted.append(c)  # insert now and delete afterwards

            # import fails if missing id
            try:
                anno = cls.create_anno(c, preserve_create=True)
            except AnnoError as e:
                msg = "error during import of anno({}): {}".format(c["id"], str(e))
                logger.error(msg, exc_info=True)
                c["error"] = msg
                discarded.append(c)
            else:
                logger.debug("imported ({})".format(c["id"]))
                imported.append(c)

        for r in reply:  # import all replies first
            logger.debug("importing reply({})".format(c["id"]))

            if "deleted" in r["platform"] and r["platform"]["deleted"]:
                logger.debug("({}) is DELETED reply".format(r["id"]))
                del r["platform"]["deleted"]  # remove before saving json
                deleted.append(r)
            try:
                anno = cls.create_anno(r, preserve_create=True)
            except AnnoError as e:
                msg = "error during import of reply anno({}): {}".format(
                    r["id"], str(e)
                )
                logger.error(msg, exc_info=True)
                r["error"] = msg
                discarded.append(r)
            else:
                logger.debug("imported reply ({})".format(r["id"]))
                imported.append(r)

        for d in deleted:  # now delete what is marked
            # deleted annotations that failed to be imported are silently ignored
            try:
                anno = Anno._default_manager.get(pk=d["id"])
            except Anno.DoesNotExist:
                logger.debug(
                    "Error deleting ({}); maybe import failed?".format(d["id"])
                )
                continue

            try:
                anno_deleted = cls.delete_anno(anno)
            except MissingAnnotationError:
                # ok to be already deleted
                continue
            except AnnoError as e:
                logger.debug("Error deleted ({})".format(d["id"]))
                msg = "error setting <soft-deleted> anno({}): {}".format(
                    d["id"], str(e)
                )
                logger.error(msg, exc_info=True)
                d["error"] = msg
                discarded.append(d)
            else:
                logger.debug("marked deleted ({})".format(d["id"]))

        resp = {
            "original_total": len(catcha_list),
            "total_success": len(imported),
            "total_failed": len(discarded),
            "imported": imported,
            "failed": discarded,
            "deleted": deleted,
            "reply": reply,
        }
        # not an annotation model list, but proper catcha jsons
        return resp

    @classmethod
    def select_annos(
        cls,
        context_id,
        collection_id=None,
        platform_name=None,
        userid_list=None,
        username_list=None,
        start_datetime=None,
        is_copy=True,
    ):
        """select a list of annotations directly from db.

        returns a QuerySet

        output list might include deleted annotations, if is_copy is False.
        NOT MEANT TO BE AN API ENDPOINT!
        """
        if is_copy:
            # exclude deleted annotations
            query = Anno._default_manager.filter(anno_deleted=False)
            # exclude replies and sort by creation date
            query = query.filter(anno_reply_to=None)
        else:  # select for export, include replies and deleted!
            query = Anno._default_manager.all()

        if username_list:
            query = query.filter(query_username(username_list))
        if userid_list:
            query = query.filter(query_userid(userid_list))
        if start_datetime:
            query = query.filter(Q(created__gt=start_datetime))

        logger.debug(
            "*************** select context_id={}, collection_id={}, platform_name={}, userid={}, username={}, start_datetime={}".format(
                context_id,
                collection_id,
                platform_name,
                userid_list,
                username_list,
                start_datetime,
            )
        )

        # ignoring platform_name assumes one platform per catchpy instance
        # see [B] below.
        search_expression = {"context_id": context_id, "collection_id": collection_id}
        if platform_name:
            search_expression["platform_name"] = platform_name

        # custom searches for platform params
        # TODO ATTENTION: assumes custom_manager extends the defaullt one,
        # provided by catchpy anno.managers.SearchManager
        q = Anno.custom_manager.search_expression(search_expression)
        if q:
            query = query.filter(q)

        query = query.order_by("-created")

        logger.debug("*************** query_len={}".format(len(query)))

        return query

    @classmethod
    def copy_annos(
        cls,
        anno_list,
        target_context_id,
        target_collection_id,
        userid_map=None,
        back_compat=False,
        fix_platform_name=False,
    ):
        """

        ATT: anno_list should not contain replies nor deleted annatations!
        for userid_map addition, see [A] below
        """

        discarded = []
        copied = []
        for a in anno_list:
            catcha = a.serialized
            catcha["id"] = generate_uid(must_be_int=back_compat)  # create new id
            catcha["platform"]["context_id"] = target_context_id
            catcha["platform"]["collection_id"] = target_collection_id
            catcha["totalReplies"] = 0
            if fix_platform_name:  # see [C] below
                catcha["platform_name"] = CATCH_DEFAULT_PLATFORM_NAME
            if userid_map:  # able to swap userid OR keep original, see [A] below
                src_userid = catcha["creator"]["id"]
                tgt_userid = userid_map.get(src_userid, src_userid)
                catcha["creator"]["id"] = tgt_userid
                catcha["permissions"]["can_read"] = []  # makes annotation public
                catcha["permissions"]["can_update"] = [tgt_userid]
                catcha["permissions"]["can_delete"] = [tgt_userid]
                catcha["permissions"]["can_admin"] = [tgt_userid]
            try:
                anno = cls.create_anno(catcha, preserve_create=True)
            except AnnoError as e:
                msg = "error during copy of anno({}): {}".format(a.anno_id, str(e))
                logger.error(msg, exc_info=True)
                catcha["error"] = msg
                discarded.append(catcha)
            else:
                copied.append(a.serialized)

        resp = {
            "original_total": len(anno_list),
            "total_success": len(copied),
            "total_failed": len(discarded),
            "success": copied,
            "failure": discarded,
        }
        return resp

    @classmethod
    def delete_annos(
        cls,
        context_id,
        collection_id=None,
        platform_name=None,
        userid_list=None,
        username_list=None,
    ):
        """delete in 2 phases, first soft-delete, then true-delete.

        if not all annotations for that given selection is soft-deleted, then
        soft-delete all. Only true-delete if all annotations is selection has
        all annotations already soft-delete.
        """
        logger.debug(
            "---------------------------- delete context_id: {}".format(context_id)
        )
        true_delete = False
        # returns no replies nor deleted
        selected = cls.select_annos(
            context_id=context_id,
            collection_id=collection_id,
            platform_name=platform_name,
            userid_list=userid_list,
            username_list=username_list,
            is_copy=True,
        )

        if len(selected) == 0:
            # means all annotations are soft deleted, so this is a true delete
            true_delete = True
            selected = cls.select_annos(
                context_id=context_id,
                collection_id=collection_id,
                platform_name=platform_name,
                userid_list=userid_list,
                username_list=username_list,
                is_copy=False,
            )

        logger.debug(
            "---------------------------- TRUE DELETE? ({})".format(true_delete)
        )
        failure = []
        success = []
        for a in selected:
            try:
                if true_delete and a.anno_deleted:
                    a.delete()
                else:
                    cls.delete_anno(a)

            except Exception as e:
                failure.append(a.serialized)
                logger.error("failed to delete annotation({}): {}".format(a.anno_id, e))
            else:
                success.append(a.serialized)

        return {
            "failed": len(failure),
            "succeeded": len(success),
            "failure": failure,
            "success": success,
        }

    @classmethod
    def copy_annos_with_replies(
        cls, anno_list, target_context_id, target_collection_id, back_compat=False
    ):
        """

        ATT: anno_list should not contain replies nor deleted annatations!
        """

        discarded = []
        copied = []
        total_replies = 0
        total_success_replies = 0
        for a in anno_list:
            catcha = a.serialized
            catcha["id"] = generate_uid(must_be_int=back_compat)  # create new id
            catcha["platform"]["context_id"] = target_context_id
            catcha["platform"]["collection_id"] = target_collection_id
            catcha["totalReplies"] = 0
            try:
                anno = cls.create_anno(catcha, preserve_create=True)
            except AnnoError as e:
                msg = "error during copy of anno({}): {}".format(a.anno_id, str(e))
                logger.error(msg, exc_info=True)
                catcha["error"] = msg
                discarded.append(catcha)
            else:
                c = anno.serialized
                c["copied_from_id"] = a.anno_id
                copied.append(c)

            total_replies = len(a.replies)
            for r in a.replies:  # copy replies
                if r.anno_deleted:  # skip deleted
                    continue

                reply = r.serialized
                reply["id"] = generate_uid(must_be_int=back_compat)
                reply["platform"]["context_id"] = target_context_id
                reply["platform"]["collection_id"] = target_collection_id
                reply["platform"]["target_source_id"] = catcha["id"]
                reply["target"]["items"][0]["source"] = catcha["id"]
                reply["totalReplies"] = 0

                try:
                    rep = cls.create_anno(reply, preserve_create=True)
                except AnnoError as e:
                    msg = "error during copy of reply({}): {}".format(r.anno_id, str(e))
                    logger.error(msg, exc_info=True)
                    reply["error"] = msg
                    discarded.append(reply)
                else:
                    total_success_replies += 1
                    a_rep = rep.serialized
                    a_rep["copied_from_id"] = r.anno_id
                    copied.append(a_rep)

        resp = {
            "original_total": len(anno_list),
            "total_success": len(copied),
            "total_replies": total_replies,
            "total_success_replies": total_success_replies,
            "total_failed": len(discarded),
            "success": copied,
            "failure": discarded,
        }
        return resp


"""
[A] 05feb21 naomi: one use-case for copy_annos() is copying instructor annotations from
    one course to its re-run or v2. In edx, userids are unique within a course, so the
    instructor userid from the source course is different from the instructors in the
    target course, thus the userid swap. As consequence, permissions have also to be
    swapped and, to make it simple and assuming these are instructor annotations, all
    copied annotations are made PUBLIC. Also, when the list of annotations to be copied
    has userids not in the userid_map, they are going to be kept as the original and
    this is probably not what you want to do. Be mindful that is is implied that all
    annotations to be copied have userids in the userid_map.
    Other thing to notice is that, as the annotations list to be copied passed as
    input argument is usually Annotation objects binded to the database, any change in
    the target annotation must be done in the catcha object. Do not change the
    Annotation object before passing it to copy_annos() (or try to save it, you'll be
    updating the original annotation!)... Changes to the target object must be done in
    copy_annos().

[B] 22mar23 nmaekawa: due to oversight in configuration, catchpy database end up with
    annotations with different platform_name that are actually meant to be in the same
    platform ("edX"). This causes problem in the copy of instructor annotations, because
    it was always required to have a platform_name value. Allowing catchpy to ignore
    platform_name mitigates the problem. Note that catchpy is still able to handle
    multiple platform_names, but the client has to be more deliberate in searches and
    specify a platform_name then.

    BEWARE that this change affects delete_annos()! If platform_name == None you will
    delete annotations from all platforms.

[C] 22mar23 nmaekawa: on top of being able to select_annos() regardless its
    platform_name, copy_annos() also overwrites the platform_name with
    CATCH_DEFAULT_PLATFORM_NAME, hopefully correctly configured now!
"""
