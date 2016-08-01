(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('TaskNotifyController', TaskNotifyController);

  /* @ngInject */
  function TaskNotifyController($mdToast, $state) {
    var taskNotify = this;

    taskNotify.hide = hide;
    taskNotify.showTask = showTask;

    function hide() {
      $mdToast.hide();
    }

    function showTask() {
      $state.go('i', {action: 'task', taskId: taskNotify.taskId});
      hide();
    }
  }
})();
