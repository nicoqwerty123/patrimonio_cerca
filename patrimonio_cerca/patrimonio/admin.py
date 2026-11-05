from django.contrib import admin

from .models import Alerta, Categoria, Favorito, RecursoCultural


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "color")


@admin.action(description="Marcar como verificado con la fuente oficial")
def marcar_verificado(modeladmin, request, queryset):
    queryset.update(verificado=True)


@admin.register(RecursoCultural)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "categoria", "comuna", "costo", "verificado", "fecha_actualizacion")
    list_filter = ("verificado", "tipo", "categoria", "comuna", "acepta_pase_cultural")
    search_fields = ("titulo", "direccion", "comuna")
    actions = [marcar_verificado]


admin.site.register(Alerta)
admin.site.register(Favorito)
