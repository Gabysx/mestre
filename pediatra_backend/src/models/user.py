from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='paciente')  # paciente, medica, admin
    nome_completo = db.Column(db.String(200), nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    endereco = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    agendamentos = db.relationship('Agendamento', backref='paciente', lazy=True, foreign_keys='Agendamento.paciente_id')
    mensagens_enviadas = db.relationship('Mensagem', backref='remetente', lazy=True, foreign_keys='Mensagem.remetente_id')
    mensagens_recebidas = db.relationship('Mensagem', backref='destinatario', lazy=True, foreign_keys='Mensagem.destinatario_id')
    documentos = db.relationship('Documento', backref='paciente', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'nome_completo': self.nome_completo,
            'telefone': self.telefone,
            'data_nascimento': self.data_nascimento.isoformat() if self.data_nascimento else None,
            'cpf': self.cpf,
            'endereco': self.endereco,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    medica_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)
    tipo_consulta = db.Column(db.String(50), nullable=False)  # primeira_consulta, retorno, teleconsulta
    status = db.Column(db.String(20), nullable=False, default='agendado')  # agendado, confirmado, cancelado, realizado
    observacoes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    medica = db.relationship('User', foreign_keys=[medica_id], backref='consultas_medica')

    def to_dict(self):
        return {
            'id': self.id,
            'paciente_id': self.paciente_id,
            'medica_id': self.medica_id,
            'data_hora': self.data_hora.isoformat(),
            'tipo_consulta': self.tipo_consulta,
            'status': self.status,
            'observacoes': self.observacoes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    remetente_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    lida = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'remetente_id': self.remetente_id,
            'destinatario_id': self.destinatario_id,
            'conteudo': self.conteudo,
            'lida': self.lida,
            'created_at': self.created_at.isoformat()
        }

class Documento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    tipo_documento = db.Column(db.String(50), nullable=False)  # receita, atestado, exame, etc.
    caminho_arquivo = db.Column(db.String(500), nullable=False)
    tamanho_arquivo = db.Column(db.Integer, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    uploaded_by_user = db.relationship('User', foreign_keys=[uploaded_by])

    def to_dict(self):
        return {
            'id': self.id,
            'paciente_id': self.paciente_id,
            'nome_arquivo': self.nome_arquivo,
            'tipo_documento': self.tipo_documento,
            'tamanho_arquivo': self.tamanho_arquivo,
            'uploaded_by': self.uploaded_by,
            'created_at': self.created_at.isoformat()
        }
