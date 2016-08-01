(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvConf', cvConf);

  /* @ngInject */
  function cvConf() {
    return {
      templateUrl: '/static/template/proxy/proxy.html',
      restrict: 'AE',
      scope: {
        cvModel: '=',
        disableHost: '@',
      }
    };
  }
})();
