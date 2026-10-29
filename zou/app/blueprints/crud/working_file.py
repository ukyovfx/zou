from flasgger import swag_from
from flask import current_app

from sqlalchemy.exc import StatementError

from zou.app.exceptions import WrongParameterException
from flask_jwt_extended import jwt_required

from zou.app.blueprints.crud.base import BaseModelsResource, BaseModelResource

from zou.app.models.entity import Entity
from zou.app.models.project import Project
from zou.app.models.working_file import WorkingFile
from zou.app.services import files_service, permissions_service, user_service
from zou.app.utils import permissions


class WorkingFilesResource(BaseModelsResource):
    def __init__(self):
        BaseModelsResource.__init__(self, WorkingFile)

    def get_relations_eager_load(self):
        return [WorkingFile.outputs]

    def check_read_permissions(self, options=None):
        """
        Require a task or entity scope for non-admin working-file queries.
        """
        if permissions.has_admin_permissions():
            return True

        options = options or {}
        task_id = options.get("task_id")
        entity_id = options.get("entity_id")
        if task_id:
            return permissions_service.check_working_file_access(task_id)
        if entity_id:
            return permissions_service.check_working_file_entity_access(
                entity_id
            )
        raise permissions.PermissionDenied

    @jwt_required()
    @swag_from("openapi/WorkingFilesResource_get.yml")
    def get(self):
        """
        Get working files
        """
        return super().get()

    @jwt_required()
    @swag_from("openapi/WorkingFilesResource_post.yml")
    def post(self):
        """
        Create working file
        """
        return super().post()

    def add_project_permission_filter(self, query):
        """
        Filtering to keep only the files from projects available to the user's
        team. Allows projects that are no longer open.
        """
        if permissions.has_admin_permissions():
            return query
        else:
            query = (
                query.join(Entity, WorkingFile.entity_id == Entity.id)
                .join(Project)
                .filter(user_service.build_team_filter())
            )
            return query


class WorkingFileResource(BaseModelResource):
    def __init__(self):
        BaseModelResource.__init__(self, WorkingFile)

    def check_read_permissions(self, instance):
        working_file = files_service.get_working_file(instance["id"])
        return permissions_service.check_working_file_access(
            working_file["task_id"]
        )

    def check_update_permissions(self, instance, data):
        working_file = files_service.get_working_file(instance["id"])
        return permissions_service.check_working_file_access(
            working_file["task_id"], require_assigned_artist=True
        )

    @jwt_required()
    @swag_from("openapi/WorkingFileResource_put.yml")
    def put(self, instance_id):
        """
        Update working file
        """
        return super().put(instance_id)

    @jwt_required()
    @swag_from("openapi/WorkingFileResource_delete.yml")
    def delete(self, instance_id):
        """
        Delete working file
        """
        return super().delete(instance_id)

    @jwt_required()
    @swag_from("openapi/WorkingFileResource_get.yml")
    def get(self, instance_id):
        """
        Get working file
        """
        try:
            working_file = files_service.get_working_file(instance_id)
            self.check_read_permissions(working_file)
            return self.clean_get_result(working_file)

        except StatementError as exception:
            current_app.logger.error(str(exception), exc_info=1)
            return {"message": str(exception)}, 400

        except ValueError:
            raise WrongParameterException("Invalid value.")

    def post_update(self, instance_dict, data):
        files_service.clear_working_file_cache(instance_dict["id"])
        return instance_dict

    def post_delete(self, instance_dict):
        files_service.clear_working_file_cache(instance_dict["id"])
        return instance_dict
