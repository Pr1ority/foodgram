from api.filters import RecipeFilter
from api.paginations import FoodgramPageNumberPagination
from api.permissions import IsAuthorOrReadOnlyPermission
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          RecipeSerializer, TagSerializer)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('-pub_date')
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = FoodgramPageNumberPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeCreateSerializer

        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        favorite_exist = Favorite.objects.filter(recipe=recipe.id,
                                                 user=user.id).exists()

        if request.method == 'POST':
            if favorite_exist:
                return Response({'status': 'рецепт уже в избранном'},
                                status=status.HTTP_400_BAD_REQUEST)
            favorite = Favorite.objects.create(recipe=recipe, user=user)
            favorite.save()
            return Response({'status': 'рецепт добавлен в избранное'},
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if favorite_exist:
                Favorite.objects.filter(user=user.id,
                                        recipe=recipe.id).delete()
                return Response({'status': 'рецепт удален из избранного'},
                                status=status.HTTP_204_NO_CONTENT)
            return Response({'status': 'рецепта нет в избранном'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        cart_item_exist = ShoppingCart.objects.filter(recipe=recipe.id,
                                                      user=user.id).exists()
        if request.method == 'POST':
            if not cart_item_exist:
                cart_item = ShoppingCart.objects.create(recipe=recipe,
                                                        user=user)
                cart_item.save()
                return Response({'status': 'рецепт добавлен в список покупок'},
                                status=status.HTTP_201_CREATED)
            return Response({'status': 'рецепт уже в списке покупок'},
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'DELETE':
            if cart_item_exist:
                ShoppingCart.objects.filter(recipe=recipe.id,
                                            user=user.id).delete()
                return Response({'status': 'рецепт удален из списка покупок'},
                                status=status.HTTP_204_NO_CONTENT)
            return Response({'status': 'рецепт не в списке покупок'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart = ShoppingCart.objects.filter(user=user)
        if not shopping_cart.exists():
            return Response({'detail': 'Ваш список покупок пуст'},
                            status=status.HTTP_400_BAD_REQUEST)
        ingredients = {}
        for item in shopping_cart:
            recipe = item.recipe
            for ingredient in recipe.ingredients.all():
                amount = RecipeIngredient.objects.get(
                    recipe=recipe, ingredient=ingredient).amount
                if ingredient.name in ingredients:
                    ingredients[ingredient.name]['amount'] += amount
                else:
                    ingredients[ingredient.name] = {
                        'measurement_unit': ingredient.measurement_unit,
                        'amount': amount
                    }
        shopping_list = [
            f"{ingredient} — {data['amount']} {data['measurement_unit']}"
            for ingredient, data in ingredients.items()
        ]
        content = '\n'.join(shopping_list)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"')
        return response


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsAuthorOrReadOnlyPermission,)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['^name']
    ordering_fields = ['name']


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsAuthorOrReadOnlyPermission,)
