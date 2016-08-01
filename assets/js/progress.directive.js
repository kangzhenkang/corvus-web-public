(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvProgress', cvProgress);

  /* @ngInject */
  function cvProgress() {
    return {
      template: '<div class="cv-progress" ng-if="cvProgress" ng-class="{\'cv-abs\': cvAbs}" >' +
                '<md-progress-circular md-mode="indeterminate" md-diameter="{{ cvDiameter }}"></md-progress-circular>' +
                '</div>',
      restrict: 'A',
      scope: {
        cvAbs: '@',
        cvDiameter: '@',
        cvProgress: '=',
      }
    };
  }
})();
