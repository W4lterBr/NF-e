# Código para adicionar ao interface_pyqt5.py antes da função main()

    # ====== SISTEMA DE SINCRONIZAÇÃO AUTOMÁTICA EM BACKGROUND ======
    
    def eventFilter(self, obj, event):
        """Detecta atividade do usuário para resetar timer de inatividade"""
        from PyQt5.QtCore import QEvent
        if event.type() in [QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel]:
            self._ultimo_evento_usuario = datetime.now()
        return super().eventFilter(obj, event)
    
    def _check_inatividade(self):
        """Verifica inatividade e inicia sincronização automática"""
        tempo_inativo = (datetime.now() - self._ultimo_evento_usuario).total_seconds()
        
        # Se inativo por mais de 30 segundos e não há sincronização rodando
        if tempo_inativo > 30 and not self._sync_worker:
            print("[AUTO-SYNC] Usuário inativo há 30s, iniciando sincronização automática...")
            self._iniciar_sync_background()
    
    def _iniciar_sync_background(self):
        """Inicia sincronização de eventos em background"""
        if self._sync_worker:
            print("[AUTO-SYNC] Sincronização já em andamento")
            return
        
        # Cria worker e thread
        from PyQt5.QtCore import QThread, pyqtSignal, QObject
        
        class SyncWorker(QObject):
            progress = pyqtSignal(str, int, int)  # mensagem, atual, total
            finished = pyqtSignal()
            error = pyqtSignal(str)
            
            def __init__(self, parent_window):
                super().__init__()
                self.parent = parent_window
                self._pausado = False
                self._cancelado = False
            
            def pausar(self):
                self._pausado = True
            
            def retomar(self):
                self._pausado = False
            
            def cancelar(self):
                self._cancelado = True
            
            def run(self):
                try:
                    # Obtém documentos
                    if self.parent.tabs.currentIndex() == 0:
                        docs = self.parent.filtered()
                    else:
                        docs = self.parent.filtered_emitidos()
                    
                    total = len(docs)
                    self.progress.emit(f"Iniciando sincronização de {total} documentos...", 0, total)
                    
                    for idx, item in enumerate(docs):
                        # Verifica se foi cancelado
                        if self._cancelado:
                            self.progress.emit("Sincronização cancelada pelo usuário", idx, total)
                            break
                        
                        # Aguarda se pausado
                        while self._pausado and not self._cancelado:
                            import time
                            time.sleep(0.5)
                        
                        if self._cancelado:
                            break
                        
                        chave = item.get('chave', '')
                        numero = item.get('numero', chave[:10])
                        
                        self.progress.emit(f"Consultando eventos - Doc {numero}", idx+1, total)
                        
                        # Consulta eventos (mesmo código de _sincronizar_eventos_lote)
                        try:
                            informante = item.get('informante', '')
                            certs = self.parent.db.load_certificates()
                            cert_uf = None
                            
                            for cert in certs:
                                if cert.get('informante') == informante:
                                    cert_uf = cert
                                    break
                            
                            if not cert_uf and certs:
                                cert_uf = certs[0]
                            
                            if cert_uf and chave and len(chave) == 44:
                                from nfe_search import NFeService
                                service = NFeService(
                                    cert_path=cert_uf.get('caminho', ''),
                                    senha=cert_uf.get('senha', ''),
                                    cnpj=cert_uf.get('informante', ''),
                                    cuf=cert_uf.get('cUF_autor', '50')
                                )
                                
                                resposta_xml = service.consultar_eventos_chave(chave)
                                
                                if resposta_xml:
                                    from lxml import etree
                                    root = etree.fromstring(resposta_xml.encode('utf-8'))
                                    eventos = root.findall('.//{http://www.portalfiscal.inf.br/nfe}retEvento')
                                    
                                    for evento in eventos:
                                        tp_evento = evento.findtext('.//{http://www.portalfiscal.inf.br/nfe}tpEvento')
                                        cstat = evento.findtext('.//{http://www.portalfiscal.inf.br/nfe}cStat')
                                        
                                        if cstat in ['135', '136'] and tp_evento:
                                            evento_xml_str = etree.tostring(evento, encoding='utf-8').decode('utf-8')
                                            
                                            from nfe_search import salvar_xml_por_certificado
                                            salvar_xml_por_certificado(
                                                evento_xml_str,
                                                cert_uf.get('informante')
                                            )
                                            
                                            if tp_evento in ['210200', '210210', '210220', '210240']:
                                                self.parent.db.register_manifestacao(
                                                    chave,
                                                    tp_evento,
                                                    cert_uf.get('informante'),
                                                    datetime.now().isoformat()
                                                )
                        
                        except Exception as e:
                            print(f"[AUTO-SYNC] Erro ao processar {numero}: {e}")
                        
                        # Delay entre requisições
                        import time
                        time.sleep(1.5)
                    
                    self.progress.emit(f"Sincronização concluída! {total} documentos processados", total, total)
                    self.finished.emit()
                    
                except Exception as e:
                    self.error.emit(str(e))
        
        # Cria thread e worker
        self._sync_thread = QThread()
        self._sync_worker = SyncWorker(self)
        self._sync_worker.moveToThread(self._sync_thread)
        
        # Conecta sinais
        self._sync_thread.started.connect(self._sync_worker.run)
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.error.connect(self._on_sync_error)
        self._sync_worker.progress.connect(self._on_sync_progress)
        
        # Adiciona à lista de trabalhos
        trabalho = {
            'id': datetime.now().timestamp(),
            'nome': 'Sincronização de Eventos',
            'tipo': 'sync_eventos',
            'status': 'Em execução',
            'progresso': 0,
            'total': 0,
            'worker': self._sync_worker,
            'thread': self._sync_thread
        }
        self._trabalhos_ativos.append(trabalho)
        
        # Inicia
        self._sync_thread.start()
        print("[AUTO-SYNC] Sincronização iniciada em background")
    
    def _on_sync_progress(self, msg, atual, total):
        """Atualiza progresso da sincronização"""
        if self._trabalhos_ativos:
            self._trabalhos_ativos[0]['progresso'] = atual
            self._trabalhos_ativos[0]['total'] = total
            self._trabalhos_ativos[0]['mensagem'] = msg
        
        # Atualiza status bar
        if total > 0:
            percentual = int((atual / total) * 100)
            self.set_status(f"🔄 {msg} ({percentual}%)")
    
    def _on_sync_finished(self):
        """Finaliza sincronização"""
        print("[AUTO-SYNC] Sincronização finalizada")
        if self._trabalhos_ativos:
            self._trabalhos_ativos[0]['status'] = 'Concluído'
        
        # Aguarda thread terminar
        if self._sync_thread:
            self._sync_thread.quit()
            self._sync_thread.wait()
        
        self._sync_worker = None
        self._sync_thread = None
        
        # Remove da lista após 5 segundos
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(5000, self._limpar_trabalhos_concluidos)
        
        self.set_status("✅ Sincronização automática concluída", 3000)
    
    def _on_sync_error(self, erro):
        """Trata erro na sincronização"""
        print(f"[AUTO-SYNC] Erro: {erro}")
        if self._trabalhos_ativos:
            self._trabalhos_ativos[0]['status'] = f'Erro: {erro}'
        
        if self._sync_thread:
            self._sync_thread.quit()
            self._sync_thread.wait()
        
        self._sync_worker = None
        self._sync_thread = None
        
        self.set_status(f"❌ Erro na sincronização: {erro}", 5000)
    
    def _limpar_trabalhos_concluidos(self):
        """Remove trabalhos concluídos da lista"""
        self._trabalhos_ativos = [t for t in self._trabalhos_ativos if t['status'] not in ['Concluído', 'Cancelado']]
    
    def _sincronizar_eventos_manual(self):
        """Sincroniza eventos manualmente (menu)"""
        if self._sync_worker:
            QMessageBox.information(
                self,
                "Sincronização em Andamento",
                "Já existe uma sincronização em andamento.\n\n"
                "Use o Gerenciador de Trabalhos para acompanhar o progresso."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Sincronizar Eventos",
            "Deseja sincronizar eventos de todos os documentos visíveis?\n\n"
            "Esta operação será executada em segundo plano e não travará a interface.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._iniciar_sync_background()
    
    def _abrir_gerenciador_trabalhos(self):
        """Abre o diálogo do Gerenciador de Trabalhos"""
        dialog = GerenciadorTrabalhosDialog(self)
        dialog.exec_()


# ====== DIÁLOGO DO GERENCIADOR DE TRABALHOS ======

class GerenciadorTrabalhosDialog(QDialog):
    """Diálogo moderno para gerenciar trabalhos em background"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("⚙️ Gerenciador de Trabalhos")
        self.resize(700, 400)
        
        layout = QVBoxLayout(self)
        
        # Cabeçalho
        header = QLabel("Gerenciador de Trabalhos em Segundo Plano")
        header_font = header.font()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Descrição
        desc = QLabel("Visualize e controle tarefas que estão sendo executadas em segundo plano.")
        desc.setStyleSheet("color: gray;")
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # Tabela de trabalhos
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Tarefa", "Status", "Progresso", "Ações", ""])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Botões inferiores
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_atualizar = QPushButton("🔄 Atualizar")
        btn_atualizar.clicked.connect(self._atualizar_lista)
        btn_layout.addWidget(btn_atualizar)
        
        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.close)
        btn_layout.addWidget(btn_fechar)
        
        layout.addLayout(btn_layout)
        
        # Timer para atualizar automaticamente
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._atualizar_lista)
        self.update_timer.start(2000)  # Atualiza a cada 2 segundos
        
        # Carrega trabalhos
        self._atualizar_lista()
    
    def _atualizar_lista(self):
        """Atualiza a lista de trabalhos"""
        trabalhos = self.parent._trabalhos_ativos
        
        self.table.setRowCount(len(trabalhos))
        
        if not trabalhos:
            # Mostra mensagem "Nenhum trabalho em andamento"
            self.table.setRowCount(1)
            item = QTableWidgetItem("Nenhum trabalho em andamento")
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 5)
            return
        
        for row, trabalho in enumerate(trabalhos):
            # Nome
            self.table.setItem(row, 0, QTableWidgetItem(trabalho['nome']))
            
            # Status
            status_item = QTableWidgetItem(trabalho['status'])
            if trabalho['status'] == 'Em execução':
                status_item.setForeground(QColor(52, 168, 83))  # Verde
            elif 'Erro' in trabalho['status']:
                status_item.setForeground(QColor(234, 67, 53))  # Vermelho
            elif trabalho['status'] == 'Pausado':
                status_item.setForeground(QColor(251, 188, 5))  # Amarelo
            self.table.setItem(row, 1, status_item)
            
            # Progresso
            total = trabalho.get('total', 0)
            atual = trabalho.get('progresso', 0)
            if total > 0:
                percentual = int((atual / total) * 100)
                progresso_text = f"{atual}/{total} ({percentual}%)"
            else:
                progresso_text = "Iniciando..."
            self.table.setItem(row, 2, QTableWidgetItem(progresso_text))
            
            # Ações
            acoes_widget = QWidget()
            acoes_layout = QHBoxLayout(acoes_widget)
            acoes_layout.setContentsMargins(4, 2, 4, 2)
            
            worker = trabalho.get('worker')
            
            if trabalho['status'] == 'Em execução':
                btn_pausar = QPushButton("⏸ Pausar")
                btn_pausar.clicked.connect(lambda checked, w=worker: self._pausar_trabalho(w))
                acoes_layout.addWidget(btn_pausar)
            elif trabalho['status'] == 'Pausado':
                btn_retomar = QPushButton("▶ Retomar")
                btn_retomar.clicked.connect(lambda checked, w=worker: self._retomar_trabalho(w))
                acoes_layout.addWidget(btn_retomar)
            
            btn_cancelar = QPushButton("🛑 Cancelar")
            btn_cancelar.clicked.connect(lambda checked, w=worker: self._cancelar_trabalho(w))
            acoes_layout.addWidget(btn_cancelar)
            
            self.table.setCellWidget(row, 3, acoes_widget)
        
        # Ajusta colunas
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 150)
    
    def _pausar_trabalho(self, worker):
        """Pausa um trabalho"""
        if worker:
            worker.pausar()
            # Atualiza status
            for t in self.parent._trabalhos_ativos:
                if t.get('worker') == worker:
                    t['status'] = 'Pausado'
            self._atualizar_lista()
    
    def _retomar_trabalho(self, worker):
        """Retoma um trabalho pausado"""
        if worker:
            worker.retomar()
            # Atualiza status
            for t in self.parent._trabalhos_ativos:
                if t.get('worker') == worker:
                    t['status'] = 'Em execução'
            self._atualizar_lista()
    
    def _cancelar_trabalho(self, worker):
        """Cancela um trabalho"""
        reply = QMessageBox.question(
            self,
            "Cancelar Trabalho",
            "Tem certeza que deseja cancelar este trabalho?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes and worker:
            worker.cancelar()
            # Atualiza status
            for t in self.parent._trabalhos_ativos:
                if t.get('worker') == worker:
                    t['status'] = 'Cancelado'
            self._atualizar_lista()
    
    def closeEvent(self, event):
        """Para o timer ao fechar"""
        self.update_timer.stop()
        event.accept()
