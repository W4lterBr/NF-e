# modules/ui_components.py
"""
Componentes de interface reutilizáveis para o sistema BOT NFe
"""

import logging
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime

try:
    import flet as ft
except ImportError:
    print("Flet não está instalado. Execute: pip install flet")
    raise

from .utils import format_currency, format_cnpj_cpf, get_status_info

logger = logging.getLogger(__name__)

class AppTheme:
    """Definições de tema da aplicação"""
    
    # Cores primárias
    PRIMARY = "#1976d2"
    PRIMARY_LIGHT = "#42a5f5"
    PRIMARY_DARK = "#1565c0"
    SECONDARY = "#0288d1"
    
    # Cores de superfície
    BACKGROUND = "#fafafa"
    SURFACE = "#ffffff"
    SURFACE_VARIANT = "#f5f5f5"
    
    # Cores de estado
    SUCCESS = "#4caf50"
    WARNING = "#ff9800"
    ERROR = "#f44336"
    INFO = "#2196f3"
    
    # Cores de texto
    TEXT_PRIMARY = "#212121"
    TEXT_SECONDARY = "#757575"
    TEXT_DISABLED = "#bdbdbd"
    
    # Tema escuro
    DARK_BACKGROUND = "#121212"
    DARK_SURFACE = "#1e1e1e"
    DARK_PRIMARY = "#90caf9"
    
    # Tipografia
    FONT_SMALL = 12
    FONT_MEDIUM = 14
    FONT_LARGE = 16
    FONT_TITLE = 20
    FONT_HEADLINE = 24
    
    # Espaçamentos
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32
    
    # Raios de borda
    RADIUS_SM = 4
    RADIUS_MD = 8
    RADIUS_LG = 12
    RADIUS_XL = 16
    
    # Elevações (sombras)
    ELEVATION_1 = ft.BoxShadow(
        spread_radius=0,
        blur_radius=2,
        color="#1A000000",  # Black with 10% opacity
        offset=ft.Offset(0, 1),
    )
    
    ELEVATION_2 = ft.BoxShadow(
        spread_radius=0,
        blur_radius=4,
        color="#26000000",  # Black with 15% opacity
        offset=ft.Offset(0, 2),
    )
    
    ELEVATION_3 = ft.BoxShadow(
        spread_radius=0,
        blur_radius=8,
        color="#33000000",  # Black with 20% opacity
        offset=ft.Offset(0, 4),
    )

class ModernCard(ft.Container):
    """Card moderno com elevação e bordas arredondadas"""
    
    def __init__(
        self,
        content,
        elevation: int = 1,
        padding: int = AppTheme.SPACING_MD,
        **kwargs
    ):
        elevations = {
            1: AppTheme.ELEVATION_1,
            2: AppTheme.ELEVATION_2,
            3: AppTheme.ELEVATION_3,
        }
        
        super().__init__(
            content=content,
            bgcolor=AppTheme.SURFACE,
            border_radius=AppTheme.RADIUS_LG,
            padding=padding,
            shadow=elevations.get(elevation, AppTheme.ELEVATION_1),
            **kwargs
        )

class ModernButton(ft.ElevatedButton):
    """Botão moderno com estilos consistentes"""
    
    def __init__(
        self,
        text: str,
        on_click: Optional[Callable] = None,
        icon: Optional[str] = None,
        variant: str = "primary",
        size: str = "medium",
        **kwargs
    ):
        # Definir cores baseadas na variante
        variants = {
            "primary": {
                "bgcolor": AppTheme.PRIMARY,
                "color": "#FFFFFF",
            },
            "secondary": {
                "bgcolor": AppTheme.SECONDARY,
                "color": "#FFFFFF",
            },
            "success": {
                "bgcolor": AppTheme.SUCCESS,
                "color": "#FFFFFF",
            },
            "warning": {
                "bgcolor": AppTheme.WARNING,
                "color": "#FFFFFF",
            },
            "error": {
                "bgcolor": AppTheme.ERROR,
                "color": "#FFFFFF",
            },
            "outline": {
                "bgcolor": "#00000000",
                "color": AppTheme.PRIMARY,
            },
        }
        
        # Definir tamanhos
        sizes = {
            "small": {"height": 32, "text_size": AppTheme.FONT_SMALL},
            "medium": {"height": 40, "text_size": AppTheme.FONT_MEDIUM},
            "large": {"height": 48, "text_size": AppTheme.FONT_LARGE},
        }
        
        variant_style = variants.get(variant, variants["primary"])
        size_style = sizes.get(size, sizes["medium"])
        
        super().__init__(
            text=text,
            icon=icon,
            on_click=on_click,
            style=ft.ButtonStyle(
                bgcolor=variant_style["bgcolor"],
                color=variant_style["color"],
                text_style=ft.TextStyle(
                    size=size_style["text_size"],
                    weight=ft.FontWeight.W_500
                ),
                shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_MD),
                elevation={"default": 2, "hovered": 4, "pressed": 1},
            ),
            height=size_style["height"],
            **kwargs
        )

class ModernTextField(ft.TextField):
    """Campo de texto moderno com validação"""
    
    def __init__(
        self,
        label: str,
        placeholder: Optional[str] = None,
        helper_text: Optional[str] = None,
        validator: Optional[Callable[[str], Optional[str]]] = None,
        **kwargs
    ):
        self.validator_func = validator
        
        super().__init__(
            label=label,
            hint_text=placeholder,
            helper_text=helper_text,
            border_radius=AppTheme.RADIUS_MD,
            text_size=AppTheme.FONT_MEDIUM,
            label_style=ft.TextStyle(size=AppTheme.FONT_MEDIUM),
            border_color="#BDBDBD",  # Grey 400
            focused_border_color=AppTheme.PRIMARY,
            on_change=self._on_change,
            **kwargs
        )
    
    def _on_change(self, e):
        """Valida o campo quando o valor muda"""
        if self.validator_func:
            error_msg = self.validator_func(self.value or "")
            self.error_text = error_msg
            self.update()

class StatusChip(ft.Container):
    """Chip de status com cores dinâmicas"""
    
    def __init__(self, status: str, size: str = "medium"):
        status_info = get_status_info(status)
        
        sizes = {
            "small": {"font_size": AppTheme.FONT_SMALL, "padding": 6, "icon_size": 14},
            "medium": {"font_size": AppTheme.FONT_MEDIUM, "padding": 8, "icon_size": 16},
            "large": {"font_size": AppTheme.FONT_LARGE, "padding": 10, "icon_size": 18},
        }
        
        size_config = sizes.get(size, sizes["medium"])
        
        super().__init__(
            content=ft.Row([
                ft.Icon(
                    getattr(ft.Icons, status_info["icon"].upper(), ft.Icons.HELP),
                    size=size_config["icon_size"],
                    color="#FFFFFF"
                ),
                ft.Text(
                    status_info["text"],
                    size=size_config["font_size"],
                    color="#FFFFFF",
                    weight=ft.FontWeight.W_500
                )
            ], tight=True, spacing=AppTheme.SPACING_XS),
            bgcolor=status_info["color"],
            border_radius=AppTheme.RADIUS_XL,
            padding=ft.padding.symmetric(
                horizontal=size_config["padding"] + 4,
                vertical=size_config["padding"]
            ),
        )

class LoadingSpinner(ft.Container):
    """Indicador de carregamento moderno"""
    
    def __init__(self, message: str = "Carregando...", size: str = "medium"):
        sizes = {
            "small": {"progress_size": 20, "font_size": AppTheme.FONT_SMALL},
            "medium": {"progress_size": 30, "font_size": AppTheme.FONT_MEDIUM},
            "large": {"progress_size": 40, "font_size": AppTheme.FONT_LARGE},
        }
        
        size_config = sizes.get(size, sizes["medium"])
        
        super().__init__(
            content=ft.Column([
                ft.ProgressRing(
                    width=size_config["progress_size"],
                    height=size_config["progress_size"],
                    color=AppTheme.PRIMARY,
                ),
                ft.Text(
                    message,
                    size=size_config["font_size"],
                    color=AppTheme.TEXT_SECONDARY,
                    text_align=ft.TextAlign.CENTER
                )
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=AppTheme.SPACING_SM),
            padding=AppTheme.SPACING_LG,
            alignment=ft.alignment.center
        )

class SearchField(ft.Container):
    """Campo de busca com ícone e ações"""
    
    def __init__(
        self,
        on_search: Optional[Callable[[str], None]] = None,
        on_clear: Optional[Callable] = None,
        placeholder: str = "Buscar...",
        **kwargs
    ):
        self.on_search = on_search
        self.on_clear = on_clear
        
        self.text_field = ft.TextField(
            hint_text=placeholder,
            border_radius=AppTheme.RADIUS_LG,
            text_size=AppTheme.FONT_MEDIUM,
            prefix_icon=ft.Icons.SEARCH,
            border_color="#E0E0E0",  # Grey 300
            focused_border_color=AppTheme.PRIMARY,
            on_change=self._on_change,
            on_submit=self._on_submit,
        )
        
        self.clear_button = ft.IconButton(
            icon=ft.Icons.CLEAR,
            icon_size=20,
            on_click=self._on_clear_click,
            visible=False,
            tooltip="Limpar busca"
        )
        
        super().__init__(
            content=ft.Row([
                ft.Container(content=self.text_field, expand=True),
                self.clear_button
            ], spacing=AppTheme.SPACING_XS),
            **kwargs
        )
    
    def _on_change(self, e):
        """Atualiza visibilidade do botão limpar"""
        has_text = bool(self.text_field.value)
        self.clear_button.visible = has_text
        self.clear_button.update()
        
        if self.on_search:
            self.on_search(self.text_field.value or "")
    
    def _on_submit(self, e):
        """Executado quando Enter é pressionado"""
        if self.on_search:
            self.on_search(self.text_field.value or "")
    
    def _on_clear_click(self, e):
        """Limpa o campo de busca"""
        self.text_field.value = ""
        self.clear_button.visible = False
        self.update()
        
        if self.on_clear:
            self.on_clear()
        elif self.on_search:
            self.on_search("")
    
    @property
    def value(self) -> str:
        """Retorna o valor atual do campo"""
        return self.text_field.value or ""
    
    @value.setter
    def value(self, new_value: str):
        """Define o valor do campo"""
        self.text_field.value = new_value
        self.clear_button.visible = bool(new_value)
        self.update()

class FilterDropdown(ft.Dropdown):
    """Dropdown para filtros com estilo consistente"""
    
    def __init__(
        self,
        label: str,
        options: List[str],
        on_change: Optional[Callable] = None,
        **kwargs
    ):
        dropdown_options = [ft.dropdown.Option(opt) for opt in options]
        
        super().__init__(
            label=label,
            options=dropdown_options,
            text_size=AppTheme.FONT_MEDIUM,
            border_radius=AppTheme.RADIUS_MD,
            border_color="#BDBDBD",  # Grey 400
            focused_border_color=AppTheme.PRIMARY,
            on_change=on_change,
            **kwargs
        )

class StatCard(ft.Container):
    """Card de estatística com ícone e valor"""
    
    def __init__(
        self,
        title: str,
        value: str,
        icon: str,
        color: str = AppTheme.PRIMARY,
        subtitle: Optional[str] = None,
        **kwargs
    ):
        content_items = [
            ft.Row([
                ft.Icon(icon, size=24, color=color),
                ft.Text(
                    title,
                    size=AppTheme.FONT_MEDIUM,
                    color=AppTheme.TEXT_SECONDARY,
                    weight=ft.FontWeight.W_500
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Text(
                value,
                size=AppTheme.FONT_HEADLINE,
                color=color,
                weight=ft.FontWeight.BOLD
            )
        ]
        
        if subtitle:
            content_items.append(
                ft.Text(
                    subtitle,
                    size=AppTheme.FONT_SMALL,
                    color=AppTheme.TEXT_SECONDARY
                )
            )
        
        super().__init__(
            content=ft.Column(
                content_items,
                spacing=AppTheme.SPACING_SM,
                tight=True
            ),
            bgcolor=AppTheme.SURFACE,
            border_radius=AppTheme.RADIUS_LG,
            padding=AppTheme.SPACING_MD,
            shadow=AppTheme.ELEVATION_1,
            **kwargs
        )

class ConfirmDialog:
    """Dialog de confirmação personalizado"""
    
    def __init__(
        self,
        page: ft.Page,
        title: str,
        message: str,
        on_confirm: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        confirm_text: str = "Confirmar",
        cancel_text: str = "Cancelar"
    ):
        self.page = page
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=AppTheme.FONT_LARGE, weight=ft.FontWeight.BOLD),
            content=ft.Text(message, size=AppTheme.FONT_MEDIUM),
            actions=[
                ft.TextButton(
                    cancel_text,
                    on_click=self._on_cancel_click,
                    style=ft.ButtonStyle(
                        color=AppTheme.TEXT_SECONDARY,
                        text_style=ft.TextStyle(size=AppTheme.FONT_MEDIUM)
                    )
                ),
                ft.ElevatedButton(
                    confirm_text,
                    on_click=self._on_confirm_click,
                    style=ft.ButtonStyle(
                        bgcolor=AppTheme.PRIMARY,
                        color="#FFFFFF",
                        text_style=ft.TextStyle(size=AppTheme.FONT_MEDIUM)
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
    
    def show(self):
        """Exibe o dialog"""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _on_confirm_click(self, e):
        """Ação de confirmação"""
        self.dialog.open = False
        self.page.update()
        
        if self.on_confirm:
            self.on_confirm()
    
    def _on_cancel_click(self, e):
        """Ação de cancelamento"""
        self.dialog.open = False
        self.page.update()
        
        if self.on_cancel:
            self.on_cancel()

class InfoDialog:
    """Dialog de informação simples"""
    
    def __init__(
        self,
        page: ft.Page,
        title: str,
        message: str,
        on_close: Optional[Callable] = None,
        button_text: str = "OK"
    ):
        self.page = page
        self.on_close = on_close
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=AppTheme.FONT_LARGE, weight=ft.FontWeight.BOLD),
            content=ft.Text(message, size=AppTheme.FONT_MEDIUM),
            actions=[
                ft.ElevatedButton(
                    button_text,
                    on_click=self._on_close_click,
                    style=ft.ButtonStyle(
                        bgcolor=AppTheme.PRIMARY,
                        color="#FFFFFF",
                        text_style=ft.TextStyle(size=AppTheme.FONT_MEDIUM)
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
    
    def show(self):
        """Exibe o dialog"""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _on_close_click(self, e):
        """Ação de fechar"""
        self.dialog.open = False
        self.page.update()
        
        if self.on_close:
            self.on_close()

class ProgressDialog:
    """Dialog com indicador de progresso"""
    
    def __init__(
        self,
        page: ft.Page,
        title: str,
        message: str = "Processando...",
        cancellable: bool = False,
        on_cancel: Optional[Callable] = None
    ):
        self.page = page
        self.on_cancel = on_cancel
        self.cancellable = cancellable
        
        actions = []
        if cancellable:
            actions.append(
                ft.TextButton(
                    "Cancelar",
                    on_click=self._on_cancel_click,
                    style=ft.ButtonStyle(
                        color=AppTheme.TEXT_SECONDARY,
                        text_style=ft.TextStyle(size=AppTheme.FONT_MEDIUM)
                    )
                )
            )
        
        self.progress_ring = ft.ProgressRing(
            width=40,
            height=40,
            color=AppTheme.PRIMARY
        )
        
        self.message_text = ft.Text(
            message,
            size=AppTheme.FONT_MEDIUM,
            text_align=ft.TextAlign.CENTER
        )
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=AppTheme.FONT_LARGE, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Container(
                    content=self.progress_ring,
                    alignment=ft.alignment.center,
                    height=60
                ),
                self.message_text
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=actions if actions else None,
            actions_alignment=ft.MainAxisAlignment.END
        )
    
    def show(self):
        """Exibe o dialog"""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def update_message(self, message: str):
        """Atualiza a mensagem do progresso"""
        self.message_text.value = message
        self.message_text.update()
    
    def close(self):
        """Fecha o dialog"""
        self.dialog.open = False
        self.page.update()
    
    def _on_cancel_click(self, e):
        """Ação de cancelamento"""
        self.close()
        
        if self.on_cancel:
            self.on_cancel()

def show_snackbar(page: ft.Page, message: str, action_label: Optional[str] = None, on_action: Optional[Callable] = None):
    """
    Exibe snackbar com mensagem
    
    Args:
        page: Página do Flet
        message: Mensagem a exibir
        action_label: Texto do botão de ação (opcional)
        on_action: Callback da ação (opcional)
    """
    action_button = None
    if action_label and on_action:
        action_button = ft.SnackBarAction(action_label, on_action)
    
    page.snack_bar = ft.SnackBar(
        content=ft.Text(message, size=AppTheme.FONT_MEDIUM),
        action=action_button,
        action_color=AppTheme.PRIMARY
    )
    page.snack_bar.open = True
    page.update()
