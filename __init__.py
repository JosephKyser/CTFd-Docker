from flask import current_app as app, render_template, request, redirect, jsonify, url_for, Blueprint
from CTFd.utils import cache
from CTFd.utils.decorators import admins_only
from CTFd.utils.user import is_admin
from CTFd.models import db
from .models import Containers

from . import utils

def load(app):
    # app.db.create_all()
    admin_containers = Blueprint('admin_containers', __name__, template_folder='templates')


    @admin_containers.route('/admin/containers', methods=['GET'])
    @admins_only
    def list_container():
        containers = Containers.query.all()
        for c in containers:
            c.status = utils.container_status(c.name)
            # we need not ports because we will proxy with nginx or kong
            c.ports = ', '.join(utils.container_ports(c.name, verbose=True))
        return render_template('containers.html', containers=containers)


    @admin_containers.route('/admin/containers/<int:container_id>/stop', methods=['POST'])
    @admins_only
    def stop_container(container_id):
        container = Containers.query.filter_by(id=container_id).first_or_404()
        if utils.container_stop(container.name):
            return '1'
        else:
            return '0'


    @admin_containers.route('/admin/containers/<int:container_id>/start', methods=['POST'])
    @admins_only
    def run_container(container_id):
        container = Containers.query.filter_by(id=container_id).first_or_404()
        if utils.container_status(container.name) == 'missing':
            if utils.run_image(container.name):
                return '1'
            else:
                return '0'
        else:
            if utils.container_start(container.name):
                return '1'
            else:
                return '0'


    @admin_containers.route('/admin/containers/<int:container_id>/delete', methods=['POST'])
    @admins_only
    def delete_container(container_id):
        container = Containers.query.filter_by(id=container_id).first_or_404()
        if utils.delete_image(container.name):
            db.session.delete(container)
            db.session.commit()
            db.session.close()
        return '1'


    @admin_containers.route('/admin/containers/new', methods=['POST'])
    @admins_only
    def new_container():
        name = request.form.get('name')
        print(set(name), set('abcdefghijklmnopqrstuvwxyz0123456789-_'), set(name) <= set('abcdefghijklmnopqrstuvwxyz0123456789-_'))
        if not set(name) <= set('abcdefghijklmnopqrstuvwxyz0123456789-_'):
            return redirect(url_for('admin_containers.list_container'))
        container = Containers.query.filter_by(name=name).first()
        if container:
            return redirect(url_for('admin_containers.list_container', error='名称已存在'))
        files = request.files.getlist('files[]')
        utils.create_image(name=name, files=files)
        utils.run_image(name)
        return redirect(url_for('admin_containers.list_container'))


    @admin_containers.route('/admin/containers/import', methods=['POST'])
    @admins_only
    def import_container():
        name = request.form.get('name')
        if not set(name) <= set('abcdefghijklmnopqrstuvwxyz0123456789-_'):
            return redirect(url_for('admin_containers.list_container', error='镜像名称不正确'))
        if utils.import_image(name=name):
            return redirect(url_for('admin_containers.list_container'))
        else:
            return redirect(url_for('admin_containers.list_container', error='镜像名称不正确'))

    app.register_blueprint(admin_containers)