import flet as ft
from .file_signature_card import FileSignature, FileSignatureCard
from datetime import datetime, timedelta

class FileSignatureCardContainer(ft.Column):
    def __init__(self, page: ft.Page):
        """Container for file signature cards"""
        super().__init__()
        self.page = page
        self.cards = ft.Column()
        self.placeholder = ft.Container(
            content=ft.Text("No file signatures found."),
            alignment=ft.alignment.center,
            expand=True,
            height=100,
        )
        self.scroll = ft.ScrollMode.AUTO
        self.expand = True
        self.controls = [
            self.placeholder,
            self.cards,
        ]

        # Initially show placeholder since no cards
        self.placeholder.visible = True

    def add_card(self, new_file_signature: FileSignature):
        new_card = FileSignatureCard(new_file_signature, self.card_delete)
        self.cards.controls.append(new_card.card)
        if len(self.cards.controls) > 0:
            self.placeholder.visible = False
        else:
            self.placeholder.visible = True
        self.page.update()

    def card_delete(self, card_instance):
        self.cards.controls.remove(card_instance.card)
        if len(self.cards.controls) == 0:
            self.placeholder.visible = True
        else:
            self.placeholder.visible = False
        self.page.update()