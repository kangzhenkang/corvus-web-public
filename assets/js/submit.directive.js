(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvSubmit', cvSubmit);

  /* @ngInject */
  function cvSubmit() {
    return {
      template: '<md-button aria-label="waitable submit"' +
                ' ng-click="cvClick()" ng-disabled="cvDisable || cvWait" class="{{ cvClass }}">' +
                '<span ng-if="!cvWait" ng-transclude></span>' +
                '<span cv-progress="cvWait" cv-diameter="30"></span>' +
                '</md-button>',
      transclude: true,
      restrict: 'E',
      scope: {
        cvClick: '&',
        cvWait: '=',
        cvDisable: '=',
        cvClass: '@',
      }
    };
  }
})();
