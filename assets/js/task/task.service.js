(function() {
  'use strict';

  var STATUS_MAP = {
    0: ['已创建', 'label-lime'],
    1: ['执行中', 'label-light-green'],
    2: ['完毕', 'label-green'],
    3: ['失败', 'label-red'],
  };

  angular
    .module('corvus')
    .service('taskService', TaskService);

  /* @ngInject */
  function TaskService($http, notify) {
    this.getStatusLabel = getStatusLabel;
    this.getStatusClass = getStatusClass;
    this.getTask = getTask;
    this.getTasks = getTasks;
    this.notifyTask = notifyTask;

    function getStatusLabel(status) {
      return STATUS_MAP[status][0];
    }

    function getTask(taskId) {
      return $http.get('/api/task/' + taskId);
    }

    function getTasks(page, filters) {
      var params = {
        page: page,
        q: {
          order_by: [{
            field: 'created_at',
            direction: 'desc',
          }]
        }
      };
      if (filters) {
        angular.extend(params.q, filters);
      }
      return $http.get('/api/task', {params: params});
    }

    function getStatusClass(status) {
      return STATUS_MAP[status][1];
    }

    function notifyTask(locals) {
      notify.message({
        templateUrl: '/static/template/taskNotify.html',
        hideDelay: 0,
        controller: 'TaskNotifyController',
        controllerAs: 'taskNotify',
        locals: locals,
        bindToController: true
      });
    }
  }
})();
