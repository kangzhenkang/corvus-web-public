(function() {
  'use strict';

  angular
    .module('corvus')
    .service('notify', Notify);

  /* @ngInject */
  function Notify($mdToast) {
    this.warn = warn;
    this.notice = notice;
    this.message = message;

    function warn(msg) {
      $mdToast.show(
        $mdToast
          .simple()
          .position('top right')
          .textContent(msg)
          .theme('warn')
      );
    }

    function notice(msg) {
      $mdToast.show(
        $mdToast
          .simple()
          .position('top right')
          .textContent(msg)
      );
    }

    function message(conf) {
      angular.extend(conf, {position: 'top right'});
      return $mdToast.show(conf);
    }
  }
})();
